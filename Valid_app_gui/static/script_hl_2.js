
document.addEventListener("DOMContentLoaded", function () {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const processBtn = document.getElementById('processBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const optionSelect = document.getElementById('optionSelect');
    const modelViewer = document.getElementById('displayContent');
    const gltfGetter = document.getElementById('gltfButton');
    const responseText = document.getElementById('responseText');
    const responseLoader = document.getElementById('responseLoader');
    const visualizeBtn = document.getElementById('visualizeBtn');
    const responseRdf = { text: "not yet" };
    const resultsPage = document.getElementById('resultparseBtn');

    function showDownload() {
        downloadBtn.style.visibility = "visible";
        visualizeBtn.style.visibility = "visible";
    }

    function showLoader() {
        responseLoader.style.visibility = "visible";
    }

    function hideLoader() {
        responseLoader.style.visibility = "hidden";
    }

    let cityjson = null;
    let cityjson2 = null; // New global variable
    let selectedID = null;
    let selectedOBJ = null;

    // --------------------------------------------------------------------
    // Shared GLB / CityJSON state — used by both the main 3D viewer and the
    // per-URI mini viewer. Loaded once via /get_gltf and cached so clicking
    // a URI item doesn't re-fetch and the mini viewer can slice triangles
    // straight out of the same batched geometry the main viewer uses.
    // --------------------------------------------------------------------
    let featureIdMap = {};            // "ID_xxx" -> integer feature id
    let parsedCityObjects = null;     // lazy parse of the uploaded CityJSON text
    let cachedBatchedGeometry = null; // { positions, indices, featureIds } typed arrays
    let glbLoadPromise = null;        // dedupes concurrent /get_gltf fetches

    function getCityObjects() {
        if (parsedCityObjects !== null) return parsedCityObjects;
        try {
            const src = (typeof cityjson === 'string' && cityjson) ||
                        (typeof cityjson2 === 'string' && cityjson2) || null;
            parsedCityObjects = src ? (JSON.parse(src).CityObjects || {}) : {};
        } catch (e) {
            console.warn("Could not parse CityJSON for child lookup:", e);
            parsedCityObjects = {};
        }
        return parsedCityObjects;
    }

    function idVariants(id) {
        const s = String(id);
        const stripped = s.replace(/^\{|\}$/g, '');
        return [s, stripped, `{${stripped}}`];
    }
    function lookupFeatureId(id) {
        for (const v of idVariants(id)) {
            if (featureIdMap[v] !== undefined) return { id: v, fid: featureIdMap[v] };
        }
        return null;
    }
    function lookupCityObject(id) {
        const cityObjects = getCityObjects();
        for (const v of idVariants(id)) {
            if (cityObjects[v]) return { id: v, obj: cityObjects[v] };
        }
        return null;
    }
    function findRenderableFallbackID(missingId) {
        const co = lookupCityObject(missingId);
        if (!co || !Array.isArray(co.obj.children)) return null;
        for (const childId of co.obj.children) {
            const m = lookupFeatureId(childId);
            if (m) return m.id;
        }
        for (const childId of co.obj.children) {
            const grand = lookupCityObject(childId);
            if (grand && Array.isArray(grand.obj.children)) {
                for (const grandId of grand.obj.children) {
                    const m = lookupFeatureId(grandId);
                    if (m) return m.id;
                }
            }
        }
        return null;
    }
    // Walk an id + all transitive children, collecting every feature integer
    // that exists in the GLB. A Building parent yields its own fid (which may
    // be empty in the GLB) plus every BuildingPart child's fid.
    function collectDescendantFeatureIds(rootId) {
        const fids = new Set();
        const visited = new Set();
        const queue = [rootId];
        while (queue.length) {
            const id = queue.shift();
            if (visited.has(id)) continue;
            visited.add(id);
            const m = lookupFeatureId(id);
            if (m) fids.add(m.fid);
            const co = lookupCityObject(id);
            if (co && Array.isArray(co.obj.children)) {
                for (const c of co.obj.children) queue.push(c);
            }
        }
        return fids;
    }

    async function buildFeatureIdMap(gltf) {
        const map = {};
        try {
            const json = gltf.parser.json;
            const ext = json.extensions && json.extensions.EXT_structural_metadata;
            if (ext && ext.propertyTables && ext.propertyTables.length > 0) {
                const table = ext.propertyTables[0];
                if (table.properties && table.properties.OBJ_ID) {
                    const valuesViewIndex = table.properties.OBJ_ID.values;
                    const offsetsViewIndex = table.properties.OBJ_ID.stringOffsets;
                    const valuesView = await gltf.parser.getDependency('bufferView', valuesViewIndex);
                    const offsetsView = await gltf.parser.getDependency('bufferView', offsetsViewIndex);
                    const offsetsArray = new Uint32Array(offsetsView);
                    const valuesArray = new Uint8Array(valuesView);
                    const decoder = new TextDecoder('utf-8');
                    for (let i = 0; i < offsetsArray.length - 1; i++) {
                        const str = decoder.decode(valuesArray.subarray(offsetsArray[i], offsetsArray[i + 1]));
                        map[str] = i;
                    }
                }
            }
        } catch (e) {
            console.warn("Could not parse EXT_structural_metadata from GLB:", e);
        }
        return map;
    }

    // Pull positions / indices / feature-id typed arrays out of the GLB's
    // batched mesh once, so the mini viewer can iterate them without
    // touching the live three.js scene.
    function extractBatchedGeometry(gltf) {
        let result = null;
        gltf.scene.traverse(child => {
            if (result) return;
            if (!(child.isMesh || child.isLine || child.isLineSegments || child.isPoints)) return;
            const geom = child.geometry;
            if (!geom || !geom.attributes) return;
            const featureIdKey = Object.keys(geom.attributes).find(k =>
                k.toLowerCase().includes('feature_id') ||
                k.toLowerCase().includes('batchid') ||
                k.toLowerCase().includes('objectid')
            );
            if (!featureIdKey) return;
            result = {
                positions: geom.attributes.position.array,
                indices: geom.index ? geom.index.array : null,
                featureIds: geom.attributes[featureIdKey].array
            };
        });
        return result;
    }

    // Ensure the GLB has been fetched + parsed at least once. Concurrent
    // callers share the same in-flight promise.
    // Fetch a 3×3 OpenStreetMap tile grid centered on (lat, lng), stitch into
    // a canvas, and drop it as a textured plane under the model so the user
    // gets geographic context. Plane is sized to the tile grid's metric span
    // at this latitude, offset so the model's geographic centroid sits at
    // world origin (plus any `refX`/`refY` residual from a later bbox shift),
    // and placed at `planeZ` — should be below the model's bounding box so it
    // doesn't slice through buildings.
    async function addOSMBasemap(scene, lat, lng, planeZ = -0.01, opts = {}) {
        if (typeof lat !== 'number' || typeof lng !== 'number' || !isFinite(lat) || !isFinite(lng)) return;
        const refX = opts.refX || 0;
        const refY = opts.refY || 0;
        const modelExtent = opts.modelExtent || 0;  // metres across the model's longest horizontal axis

        const EARTH_CIRC = 40075016.686;
        const latRad = lat * Math.PI / 180;
        const half = 1;            // 3×3 grid
        const grid = 2 * half + 1;

        // Pick the zoom such that the 3×3 grid covers the whole model with a
        // bit of padding. Hard-coding z=18 cropped large models to a centre
        // strip.
        let z;
        if (modelExtent > 0) {
            const padding = 1.3;
            const desiredTileMeters = (modelExtent * padding) / grid;
            const ideal = Math.log2((EARTH_CIRC * Math.cos(latRad)) / desiredTileMeters);
            z = Math.max(10, Math.min(19, Math.floor(ideal)));
        } else {
            z = 18;
        }
        const n = Math.pow(2, z);
        const xFrac = (lng + 180) / 360 * n;
        const yFrac = (1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2 * n;
        const xTile = Math.floor(xFrac);
        const yTile = Math.floor(yFrac);

        const tilePx = 256;
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = tilePx * grid;
        const ctx = canvas.getContext('2d');
        // Placeholder fill so the plane is visible before any tile lands.
        ctx.fillStyle = '#e6ecef';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Metric size of one tile at this latitude (Web Mercator).
        const tileMeters = (EARTH_CIRC * Math.cos(latRad)) / n;
        const planeSize = tileMeters * grid;

        // Position the plane so the geographic centroid maps to world origin,
        // *then* add the residual (refX, refY) — the JS-side bbox recenter in
        // viewWhole shifts the mean centroid away from world origin for
        // asymmetric models, so the basemap has to compensate or it'll drift
        // off from the buildings.
        const offsetX = -((xFrac - xTile - 0.5) * tileMeters) + refX;
        const offsetY = (yFrac - yTile - 0.5) * tileMeters + refY;

        const texture = new THREE.CanvasTexture(canvas);
        texture.anisotropy = 4;
        const planeGeom = new THREE.PlaneGeometry(planeSize, planeSize);
        const planeMat = new THREE.MeshBasicMaterial({
            map: texture,
            side: THREE.DoubleSide
        });
        const plane = new THREE.Mesh(planeGeom, planeMat);
        // Sit below the model's bounding box so the basemap is unambiguously
        // *under* every building — normal depth testing then keeps buildings
        // in front from every camera angle.
        plane.position.set(offsetX, offsetY, planeZ);
        plane.renderOrder = -1;
        plane.userData.isBasemap = true;
        scene.add(plane);
        console.log(`[basemap] z=${z}, tile=${tileMeters.toFixed(1)}m, plane=${planeSize.toFixed(1)}m, pos=(${offsetX.toFixed(1)},${offsetY.toFixed(1)},${planeZ.toFixed(1)})`);

        // Kick off the nine tile fetches and paint each one as it arrives —
        // don't block the plane's creation on Promise.all (any single tile
        // failing would otherwise sink the whole basemap), and don't wait
        // until the slowest tile loads before showing anything.
        let loaded = 0, failed = 0;
        for (let dy = -half; dy <= half; dy++) {
            for (let dx = -half; dx <= half; dx++) {
                const tx = xTile + dx, ty = yTile + dy;
                if (tx < 0 || ty < 0 || tx >= n || ty >= n) continue;
                const url = `https://tile.openstreetmap.org/${z}/${tx}/${ty}.png`;
                const img = new Image();
                img.crossOrigin = 'anonymous';
                img.onload = () => {
                    ctx.drawImage(img, (dx + half) * tilePx, (dy + half) * tilePx);
                    texture.needsUpdate = true;
                    loaded++;
                };
                img.onerror = () => {
                    failed++;
                    console.warn(`OSM tile failed: ${url}`);
                };
                img.src = url;
            }
        }
    }

    async function ensureGlbData() {
        if (cachedBatchedGeometry && Object.keys(featureIdMap).length > 0) {
            return { featureIdMap, batchedGeometry: cachedBatchedGeometry };
        }
        if (!glbLoadPromise) {
            glbLoadPromise = (async () => {
                if (!cityjson) throw new Error("Upload a CityJSON file first.");
                const formData = new FormData();
                const blob = typeof cityjson === 'string'
                    ? new Blob([cityjson], { type: 'application/json' })
                    : cityjson;
                formData.append('file', blob);
                const epsgOverride = getEpsgOverride();
                if (epsgOverride) formData.append('epsg', epsgOverride);
                const resp = await fetch('/get_gltf', { method: 'POST', body: formData });
                if (!resp.ok) throw new Error(`get_gltf failed: ${resp.status} ${resp.statusText}`);
                const data = await resp.json();
                const glbUrl = `${window.location.protocol}//${window.location.host}/download/${data.response}`;
                const gltf = await new Promise((res, rej) => {
                    new THREE.GLTFLoader().load(glbUrl, res, undefined, rej);
                });
                featureIdMap = await buildFeatureIdMap(gltf);
                cachedBatchedGeometry = extractBatchedGeometry(gltf);
                return { featureIdMap, batchedGeometry: cachedBatchedGeometry };
            })();
        }
        return glbLoadPromise;
    }

    // Collapse/expand the validation report so it doesn't dominate the screen.
    const toggleResponseBtn = document.getElementById('toggleResponseBtn');
    function applyResponseCollapsed(collapsed) {
        responseText.classList.toggle('collapsed', collapsed);
        toggleResponseBtn.textContent = collapsed ? '+' : '−';
        const label = collapsed ? 'Expand validation report' : 'Collapse validation report';
        toggleResponseBtn.setAttribute('aria-label', label);
        toggleResponseBtn.title = label;
    }
    applyResponseCollapsed(localStorage.getItem('responseCollapsed') === '1');

    // EPSG override input. We intentionally don't pre-fill from localStorage
    // — page refresh = clean slate. The field's live value is read on every
    // /get_gltf request below.
    const epsgInput = document.getElementById('epsgOverride');
    function getEpsgOverride() {
        const v = (epsgInput && epsgInput.value.trim()) || '';
        return /^\d+$/.test(v) ? v : null;
    }

    // "Apply" beside the EPSG input. Validates, persists, and re-runs the
    // GLB pipeline so the basemap regenerates with the new EPSG.
    const applyEpsgBtn = document.getElementById('applyEpsgBtn');
    if (applyEpsgBtn) {
        applyEpsgBtn.addEventListener('click', () => {
            const value = (epsgInput && epsgInput.value.trim()) || '';
            if (value && !/^\d+$/.test(value)) {
                responseText.textContent = "EPSG must be a positive integer.";
                responseText.style.color = "red";
                return;
            }
            if (!cityjson2) {
                responseText.textContent = "Upload a CityJSON file first.";
                responseText.style.color = "red";
                return;
            }
            // Reuse the View Full Model flow — its click handler already reads
            // epsgInput.value live and POSTs it.
            gltfGetter.click();
        });
    }

    // Hitting Enter inside the EPSG field also submits.
    if (epsgInput) {
        epsgInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                e.preventDefault();
                applyEpsgBtn && applyEpsgBtn.click();
            }
        });
    }
    toggleResponseBtn.addEventListener('click', function () {
        const collapsed = !responseText.classList.contains('collapsed');
        applyResponseCollapsed(collapsed);
        localStorage.setItem('responseCollapsed', collapsed ? '1' : '0');
    });

    resultsPage.addEventListener('click', function () {
        window.open(resultsPage.dataset.url, '_blank');
    }
    );

    uploadBtn.addEventListener('click', function () {
        const file = fileInput.files[0];
        if (file) {
            const formData = new FormData();
            formData.append('file', file);

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
                .then(response => response.text())
                .then(data => {
                    cityjson = data;
                    cityjson2 = data;
                    responseText.textContent = "File uploaded successfully.";
                    responseText.style.color = "green";

                })
                .catch(error => {
                    responseText.textContent = "Error uploading file.";
                    responseText.style.color = "red";
                });
        } else {
            responseText.textContent = "Please select a file to upload.";
            responseText.style.color = "red";
        }
    });

    processBtn.addEventListener('click', function () {
        const selectedOption = optionSelect.value;

        if (!cityjson) {
            responseText.textContent = "Please upload a CityJSON file.";
            responseText.style.color = "red";
            return;
        }

        const formData = new FormData();
        formData.append('cityjson', cityjson);
        formData.append('ontology', selectedOption);

        showLoader();
        fetch('/process_texts', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                responseText.textContent = data.response;
                responseRdf.text = data.rdf;
                console.log(responseRdf.text);
                hideLoader();
                showDownload();
                responseText.style.color = "green";
            })
            .catch(error => {
                console.error("Error details:", error.message);
                responseText.textContent = "Error processing data.";
                responseText.style.color = "red";
            });
    });

    downloadBtn.addEventListener('click', function () {
        if (responseText.textContent.includes("Validation Report")) {
            const reportContent = responseText.textContent;

            const blob = new Blob([reportContent], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'report.txt';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            responseText.textContent = "Please process the data before downloading the report.";
            responseText.style.color = "red";
        }
    });

    visualizeBtn.addEventListener('click', function () {
        if (responseText.textContent.includes("Validation Report")) {
            // Prepare the data to send
            const payload = {
                shacl: responseText.textContent, // SHACL validation results
                rdf: responseRdf.text // Turtle data
            };
            showLoader();

            // Send the data as JSON
            fetch('/visualize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json', // Set the content type to JSON
                },
                body: JSON.stringify(payload) // Send the data as JSON
            })
                .then(response => response.json())
                .then(data => {
                    console.log(data.response); // Handle the response from the server
                    hideLoader();

                    // Process the JSON data and render 3D visualizations
                    processJsonData(data.response);
                })
                .catch(error => {
                    console.error("Error details:", error.message);
                    responseText.textContent = "Error visualizing data.";
                    responseText.style.color = "red";
                    hideLoader();
                });
        }
    });

    gltfGetter.addEventListener('click', function () {
        if (!cityjson2) {
            responseText.textContent = "Please upload a CityJSON file first.";
            responseText.style.color = "red";
            return;
        }
        
        const formData = new FormData();
        if (typeof cityjson2 === 'string') {
            cityjson2 = new Blob([cityjson2], { type: 'application/json' });
        }
        formData.append('file', cityjson2);
        // Optional manual EPSG override for files whose metadata.referenceSystem
        // is missing or in a format the server can't parse (Vienna/Montreal).
        const epsgOverride = getEpsgOverride();
        if (epsgOverride) formData.append('epsg', epsgOverride);

        fetch('/get_gltf', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
        // Dynamically construct the absolute URL
            const glbFileName = data.response;
            const baseUrl = `${window.location.protocol}//${window.location.host}`;
            const glbUrl = `${baseUrl}/download/${glbFileName}`;

            console.log("Constructed GLB URL:", glbUrl); // Debugging
            viewWhole(glbUrl, { lat: data.lat, lng: data.lng });

        })
        .catch(error => {
            console.error("Error fetching GLB file:", error.message);
            responseText.textContent = "Error fetching GLB file.";
            responseText.style.color = "red";
        });
    });
    
    // Function to process JSON data and create 3D visualizations
    function processJsonData(jsonData) {
        const CHUNK_SIZE = 100; // Number of URIs to process at a time
        let keys = Object.keys(jsonData); // Store the keys of the JSON object
        let currentIndex = 0; // Track the current processing index

        // Per-URI mini viewer. Instead of parsing the WKT in jsonData[objectURI]
        // (which loses the GLB's already-correct earcut triangulation and forces
        // us to re-triangulate in JS), we slice the matching triangles directly
        // out of the cached batched GLB geometry. Z-up faces (normal.z > 0.7)
        // get coloured red.
        async function create3DViewer(container, objectId) {
            THREE.Object3D.DefaultUp.set(0, 0, 1);

            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(60, container.offsetWidth / container.offsetHeight, 0.001, 1000);
            camera.up.set(0, 0, 1);
            const renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(container.offsetWidth, container.offsetHeight);
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            container.appendChild(renderer.domElement);
            renderer.setClearColor(0x87ceeb);

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.55);
            scene.add(ambientLight);
            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.9);
            directionalLight.position.set(5, 5, 8).normalize();
            scene.add(directionalLight);

            // Make sure the GLB is loaded and the batched arrays are cached.
            let batchedGeometry;
            try {
                ({ batchedGeometry } = await ensureGlbData());
            } catch (e) {
                console.warn("Could not load GLB for mini viewer:", e);
                return;
            }
            if (!batchedGeometry) {
                console.warn("GLB has no batched mesh with feature ids; cannot extract per-object triangles.");
                return;
            }
            const { positions, indices, featureIds } = batchedGeometry;

            // Resolve the clicked id + all transitive children → set of
            // feature integers we want triangles for.
            const targetFids = collectDescendantFeatureIds(objectId);
            if (targetFids.size === 0) {
                console.warn(`No feature IDs in the GLB for "${objectId}".`);
                return;
            }

            // Walk triangles once; bucket them by face-normal Z so we can issue
            // one MeshPhong per colour at the end.
            const upVerts = [];     // normal.z > 0.7 (roofs / horizontal up) → red
            const otherVerts = [];  // walls / sloped / floors → gray

            function pushTriangle(ax, ay, az, bx, by, bz, cxp, cyp, czp) {
                const e1x = bx - ax, e1y = by - ay, e1z = bz - az;
                const e2x = cxp - ax, e2y = cyp - ay, e2z = czp - az;
                const nx = e1y * e2z - e1z * e2y;
                const ny = e1z * e2x - e1x * e2z;
                const nz = e1x * e2y - e1y * e2x;
                const L = Math.hypot(nx, ny, nz) || 1;
                const target = (nz / L) > 0.7 ? upVerts : otherVerts;
                target.push(ax, ay, az, bx, by, bz, cxp, cyp, czp);
            }

            if (indices) {
                for (let i = 0; i + 2 < indices.length; i += 3) {
                    const a = indices[i], b = indices[i + 1], c = indices[i + 2];
                    if (!targetFids.has(Math.round(featureIds[a]))) continue;
                    pushTriangle(
                        positions[a * 3],     positions[a * 3 + 1], positions[a * 3 + 2],
                        positions[b * 3],     positions[b * 3 + 1], positions[b * 3 + 2],
                        positions[c * 3],     positions[c * 3 + 1], positions[c * 3 + 2]
                    );
                }
            } else {
                for (let i = 0; i + 2 < featureIds.length; i += 3) {
                    if (!targetFids.has(Math.round(featureIds[i]))) continue;
                    pushTriangle(
                        positions[i * 3],       positions[i * 3 + 1],       positions[i * 3 + 2],
                        positions[(i + 1) * 3], positions[(i + 1) * 3 + 1], positions[(i + 1) * 3 + 2],
                        positions[(i + 2) * 3], positions[(i + 2) * 3 + 1], positions[(i + 2) * 3 + 2]
                    );
                }
            }

            if (upVerts.length === 0 && otherVerts.length === 0) {
                console.warn(`No triangles matched the feature ids for "${objectId}".`);
                return;
            }

            // Uniform centre + scale so the object reads at the same apparent
            // size regardless of its model-space footprint.
            let minX = Infinity, minY = Infinity, minZ = Infinity;
            let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
            function scanBounds(arr) {
                for (let i = 0; i < arr.length; i += 3) {
                    const x = arr[i], y = arr[i + 1], z = arr[i + 2];
                    if (x < minX) minX = x; if (x > maxX) maxX = x;
                    if (y < minY) minY = y; if (y > maxY) maxY = y;
                    if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
                }
            }
            scanBounds(upVerts);
            scanBounds(otherVerts);
            const cx = (minX + maxX) / 2;
            const cy = (minY + maxY) / 2;
            const cz = (minZ + maxZ) / 2;
            const range = Math.max(maxX - minX, maxY - minY, maxZ - minZ) || 1;
            const sc = 1 / range;

            function buildMesh(verts, color) {
                if (verts.length === 0) return null;
                const out = new Float32Array(verts.length);
                for (let i = 0; i < verts.length; i += 3) {
                    out[i]     = (verts[i]     - cx) * sc;
                    out[i + 1] = (verts[i + 1] - cy) * sc;
                    out[i + 2] = (verts[i + 2] - cz) * sc;
                }
                const geom = new THREE.BufferGeometry();
                geom.setAttribute('position', new THREE.BufferAttribute(out, 3));
                geom.computeVertexNormals();
                const material = new THREE.MeshPhongMaterial({
                    color,
                    shininess: 60,
                    side: THREE.DoubleSide
                });
                return new THREE.Mesh(geom, material);
            }

            const redMesh = buildMesh(upVerts, 0xf44336);
            const grayMesh = buildMesh(otherVerts, 0x808080);
            if (redMesh) scene.add(redMesh);
            if (grayMesh) scene.add(grayMesh);

            camera.position.set(1.4, 1.4, 1.1);
            camera.lookAt(0, 0, 0);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.target.set(0, 0, 0);
            controls.enableDamping = true;
            controls.dampingFactor = 0.25;
            // Three.js defaults: left-drag rotates, right-drag pans, wheel zooms.
            controls.mouseButtons = {
                LEFT: THREE.MOUSE.ROTATE,
                MIDDLE: THREE.MOUSE.DOLLY,
                RIGHT: THREE.MOUSE.PAN
            };
            controls.update();

            function animate() {
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }
            animate();
        }

        // Function to populate the URI list with a chunk of data
        function populateUriListChunk() {
            const uriList = document.getElementById("uriList");

            for (let i = 0; i < CHUNK_SIZE && currentIndex < keys.length; i++) {
                const objectURI = keys[currentIndex];

                // Create a list item for the URI
                const listItem = document.createElement("li");
                listItem.textContent = objectURI;

                // Create a container for the 3D viewer
                const viewerContainer = document.createElement("div");
                viewerContainer.className = "viewer-container";
                // Stop drag interactions inside the canvas from bubbling up to
                // the <li>'s click handler — otherwise releasing the left
                // mouse button after an OrbitControls rotate fires `click` on
                // the list item and toggles the viewer shut.
                ['click', 'dblclick', 'contextmenu'].forEach(evt =>
                    viewerContainer.addEventListener(evt, e => e.stopPropagation())
                );

                // Track whether the viewer is open
                let isViewerOpen = false;

                // Click on the LI: extract the id once, then both highlight
                // in the main viewer AND toggle the mini viewer. Doing it here
                // (instead of a separate <ul> listener) avoids relying on event
                // bubbling and the `event.target` gate that broke after we
                // added stopPropagation to viewerContainer.
                listItem.addEventListener("click", () => {
                    const text = listItem.textContent || objectURI;
                    let objectId;
                    if (text.includes("#")) objectId = text.split("#")[1].trim();
                    else if (text.includes(":")) objectId = text.split(":").pop().trim();
                    else objectId = text.trim();
                    selectedID = objectId;

                    // Trigger main-viewer highlight + auto-zoom if a viewer is
                    // up. _currentStartZoom is set by viewWhole's loader.
                    const ul = document.getElementById("uriList");
                    if (ul && ul._currentStartZoom) {
                        ul._currentStartZoom(objectId);
                    }

                    // Toggle the per-URI mini viewer.
                    if (isViewerOpen) {
                        viewerContainer.classList.remove("visible");
                        viewerContainer.innerHTML = "";
                        isViewerOpen = false;
                    } else {
                        viewerContainer.classList.add("visible");
                        console.log("Mini-viewer extracting", objectId);
                        create3DViewer(viewerContainer, objectId);
                        isViewerOpen = true;
                    }
                });

                // Append the viewer container to the URI list item
                listItem.appendChild(viewerContainer);
                uriList.appendChild(listItem);

                currentIndex++;
            }

            // Update progress bar
            const progress = (currentIndex / keys.length) * 100;
            document.getElementById("progressBar").style.width = `${progress}%`;
            document.getElementById("progressBar").textContent = `${Math.round(progress)}%`;

            // Continue processing if there are more keys
            if (currentIndex < keys.length) {
                setTimeout(populateUriListChunk, 10); // Process next chunk after a short delay
            }
        }

        // Start processing the data in chunks
        populateUriListChunk();
    }
    
    function viewWhole(glbdata, meta = {}) {
        const container = document.getElementById('displayContent');

        // Clicking "View Full Model" or "Apply EPSG" again creates a brand-new
        // scene + renderer. Without clearing the previous canvas, the new one
        // appends *below* the old one inside the fixed-height container, the
        // old (now-stale) canvas stays visible, and highlights drawn on the
        // new scene are invisible to the user. Stop any prior animate loops
        // by clearing the previous flag too.
        if (container._stopPrev) container._stopPrev();
        while (container.firstChild) container.removeChild(container.firstChild);
        const stopFlag = { stopped: false };
        container._stopPrev = () => { stopFlag.stopped = true; };

        // CityJSON is Z-up; tell three.js to treat Z as up so the model is
        // oriented correctly and OrbitControls rotates around the right axis.
        THREE.Object3D.DefaultUp.set(0, 0, 1);

        // Initialize scene, camera, and renderer
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(
            75,
            container.offsetWidth / container.offsetHeight,
            0.1,
            100000
        );
        camera.up.set(0, 0, 1);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(container.offsetWidth, container.offsetHeight);
        renderer.setClearColor(0xffffff, 1);
        container.appendChild(renderer.domElement);
    
        // Add lighting to the scene
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
        scene.add(ambientLight);
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(500, 500, 500).normalize();
        scene.add(directionalLight);
    
        // featureIdMap, parsedCityObjects, lookupFeatureId/CityObject,
        // findRenderableFallbackID and buildFeatureIdMap all live at the
        // DOMContentLoaded scope above so the per-URI mini viewer reuses them.
        // Only the per-scene highlight mesh is local to this viewer instance.
        let currentHighlightMesh = null;

        // Walk the batched mesh's indices, keep triangles whose _FEATURE_ID_0
        // matches the target integer, and build a standalone red highlight mesh
        // in the same parent so it inherits the model's transforms.
        function highlightBatchedFeature(batchedMesh, targetFeatureId) {
            const geometry = batchedMesh.geometry;
            const position = geometry.attributes.position;
            const attrs = geometry.attributes;
            const featureIdKey = Object.keys(attrs).find(k =>
                k.toLowerCase().includes('feature_id') ||
                k.toLowerCase().includes('batchid') ||
                k.toLowerCase().includes('objectid')
            );
            if (!featureIdKey) return null;

            const featureIds = attrs[featureIdKey];
            const targetId = Number(targetFeatureId);
            const highlightPositions = [];
            let matchCount = 0;

            const isLines = batchedMesh.isLine || batchedMesh.isLineSegments;
            const isPoints = batchedMesh.isPoints;
            const stride = isLines ? 2 : (isPoints ? 1 : 3);

            if (geometry.index) {
                const index = geometry.index;
                for (let i = 0; i < index.count; i += stride) {
                    const a = index.getX(i);
                    if (Math.round(featureIds.getX(a)) === targetId) {
                        matchCount++;
                        highlightPositions.push(position.getX(a), position.getY(a), position.getZ(a));
                        if (stride >= 2) {
                            const b = index.getX(i + 1);
                            highlightPositions.push(position.getX(b), position.getY(b), position.getZ(b));
                        }
                        if (stride === 3) {
                            const c = index.getX(i + 2);
                            highlightPositions.push(position.getX(c), position.getY(c), position.getZ(c));
                        }
                    }
                }
            } else {
                for (let i = 0; i < position.count; i += stride) {
                    if (Math.round(featureIds.getX(i)) === targetId) {
                        matchCount++;
                        for (let j = 0; j < stride; j++) {
                            highlightPositions.push(position.getX(i + j), position.getY(i + j), position.getZ(i + j));
                        }
                    }
                }
            }

            if (matchCount === 0) return null;

            const highlightGeo = new THREE.BufferGeometry();
            highlightGeo.setAttribute('position', new THREE.Float32BufferAttribute(highlightPositions, 3));

            let newHighlight;
            if (isLines) {
                newHighlight = new THREE.LineSegments(highlightGeo, new THREE.LineBasicMaterial({ color: 0xf44336, depthTest: false }));
            } else if (isPoints) {
                newHighlight = new THREE.Points(highlightGeo, new THREE.PointsMaterial({ color: 0xf44336, size: 0.5, depthTest: false }));
            } else {
                const mat = new THREE.MeshStandardMaterial({
                    color: 0xf44336,
                    side: THREE.DoubleSide,
                    polygonOffset: true,
                    polygonOffsetFactor: -0.1,
                    polygonOffsetUnits: -1.0
                });
                newHighlight = new THREE.Mesh(highlightGeo, mat);
                const edgesGeometry = new THREE.EdgesGeometry(highlightGeo);
                const edges = new THREE.LineSegments(edgesGeometry, new THREE.LineBasicMaterial({ color: 0xf44336, depthTest: false }));
                newHighlight.add(edges);
            }

            newHighlight.position.copy(batchedMesh.position);
            newHighlight.rotation.copy(batchedMesh.rotation);
            newHighlight.scale.copy(batchedMesh.scale);
            batchedMesh.parent.add(newHighlight);
            return newHighlight;
        }

        // Aggressive fallback for older non-batched GLBs: matches name, uuid,
        // and any string lurking in userData (gmlid, OBJ_ID, etc.).
        function findObjectByNameOrUUID(model, id) {
            let targetObject = null;
            const cleanId = String(id).trim();
            model.traverse((child) => {
                if (targetObject) return;
                let isMatch = false;
                if ((child.name && child.name.includes(cleanId)) || child.uuid === cleanId) {
                    isMatch = true;
                } else if (child.userData) {
                    if (child.userData.id === cleanId ||
                        child.userData.name === cleanId ||
                        child.userData.OBJ_ID === cleanId ||
                        child.userData.gmlid === cleanId) {
                        isMatch = true;
                    } else {
                        try {
                            const s = JSON.stringify(child.userData);
                            if (s.includes(`"${cleanId}"`)) isMatch = true;
                        } catch (e) { /* ignore circular refs */ }
                    }
                }
                if (isMatch) {
                    if (child.isMesh) {
                        targetObject = child;
                    } else {
                        let firstMesh = null;
                        child.traverse(d => { if (!firstMesh && d.isMesh) firstMesh = d; });
                        targetObject = firstMesh || child;
                    }
                }
            });
            return targetObject;
        }

        // Add OrbitControls for interactivity (created before load so we can
        // retarget them once we know the model's bounding box).
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.screenSpacePanning = false;
        // The moment the user grabs the view, hand control back to them and
        // stop the auto-zoom loop from stomping on their drag.
        controls.addEventListener('start', () => { isAutoZooming = false; });

        // Load the GLB model
        const loader = new THREE.GLTFLoader();
        loader.load(
            glbdata,
            async function (gltf) {
                featureIdMap = await buildFeatureIdMap(gltf);
                // Cache typed arrays so the per-URI mini viewer can extract
                // triangles without re-fetching the GLB.
                if (!cachedBatchedGeometry) cachedBatchedGeometry = extractBatchedGeometry(gltf);
                console.log("Feature ID map entries:", Object.keys(featureIdMap).length);

                const model = gltf.scene;
                scene.add(model);

                // Clamp the model to ground: horizontally centre it on the
                // bbox so framing is consistent, but vertically pin its
                // *bottom* to world z=0 so the basemap can sit just under it
                // and the building reads as standing on the OSM tile.
                const box = new THREE.Box3().setFromObject(model);
                const center = box.getCenter(new THREE.Vector3());
                model.position.x -= center.x;
                model.position.y -= center.y;
                model.position.z -= box.min.z;

                const size = box.getSize(new THREE.Vector3());
                const radius = 0.5 * Math.max(size.x, size.y, size.z) || 1;
                const distance = radius * 3;
                const verticalCenter = size.z / 2;  // bbox centre after the shift

                // Drop an OSM basemap under the model. Horizontal residual
                // (`-center`) compensates for the bbox-centring shift in X/Y
                // so the lat/lng anchor (which corresponds to the mean centroid
                // recentred by glb_writer) lands where the buildings actually
                // are. Z: just below ground level (z=0) to avoid z-fighting.
                if (meta && meta.lat != null && meta.lng != null) {
                    const groundZ = -Math.max(size.z * 0.002, 0.05);
                    console.log("[basemap] adding OSM basemap, anchor=", meta.lat, meta.lng,
                                "modelExtent=", Math.max(size.x, size.y),
                                "residual=", -center.x, -center.y);
                    addOSMBasemap(scene, meta.lat, meta.lng, groundZ, {
                        refX: -center.x,
                        refY: -center.y,
                        modelExtent: Math.max(size.x, size.y)
                    }).catch(e =>
                        console.warn("OSM basemap could not be added:", e));
                } else {
                    console.warn("[basemap] skipped: no lat/lng from /get_gltf. meta=", meta);
                }

                // Camera frames the model's vertical centre, not world origin
                // — origin is now the ground plane, so looking there would
                // sink the building below the screen for tall models.
                camera.position.set(distance, distance, verticalCenter + distance * 0.8);
                camera.near = Math.max(distance / 1000, 0.01);
                camera.far = distance * 100;
                camera.updateProjectionMatrix();
                camera.lookAt(0, 0, verticalCenter);

                controls.target.set(0, 0, verticalCenter);
                controls.minDistance = radius * 0.1;
                controls.maxDistance = radius * 50;
                controls.update();

                // Add edges to the mesh
                model.traverse(child => {
                    if (child.isMesh && child.geometry) {
                        const edgesGeometry = new THREE.EdgesGeometry(child.geometry);
                        const edgesMaterial = new THREE.LineBasicMaterial({ color: 0x000000 });
                        const edges = new THREE.LineSegments(edgesGeometry, edgesMaterial);
                        child.add(edges);
                    }
                });

                // Start the animation loop
                animate();
            },
            undefined,
            function (error) {
                console.error('An error occurred while loading the GLB file:', error);
            }
        );
    
        // Track zoom-in state
        let isAutoZooming = false; // Flag to control automatic zoom behavior
        let previousOBJ = null; // Store the previously selected object
        let originalMaterials = {}; // Store original materials for restoration
    
        // Animation loop
        function animate() {
            requestAnimationFrame(animate);
    
            // Update controls (if damping is enabled)
            controls.update();

            // Perform zoom-in animation if isAutoZooming is true.
            if (selectedOBJ && isAutoZooming) {
                // Target distance is proportional to the highlighted object's
                // size so we don't end up inside it on tiny objects or stay
                // miles away from city-scale ones.
                const angleOffset = Math.PI / 6;
                const boundingBox = new THREE.Box3().setFromObject(selectedOBJ);
                const center = boundingBox.getCenter(new THREE.Vector3());
                const objSize = boundingBox.getSize(new THREE.Vector3());
                const radius = 0.5 * Math.max(objSize.x, objSize.y, objSize.z) || 1;
                const targetDistance = radius * 3;  // ~3× object radius reads well

                controls.target.copy(center);

                // Same-side direction (centre→camera). The previous code used
                // camera→centre, which placed the destination on the opposite
                // side of the object — the camera oscillated and never settled.
                const fromCenter = camera.position.clone().sub(center);
                const currentDistance = fromCenter.length() || 1;
                fromCenter.divideScalar(currentDistance);  // normalize

                const verticalOffset = new THREE.Vector3(0, 0, Math.sin(angleOffset) * targetDistance);
                const newPosition = center.clone()
                    .add(fromCenter.multiplyScalar(targetDistance))
                    .add(verticalOffset);

                camera.position.lerp(newPosition, 0.15);
                camera.lookAt(controls.target);

                // Stop once we're close enough; otherwise the lerp asymptotes
                // and the loop keeps stomping on user input forever.
                if (camera.position.distanceTo(newPosition) < radius * 0.05) {
                    isAutoZooming = false;
                }
            }
    
            // Render the scene
            renderer.render(scene, camera);
        }
    
        // Function to start zoom animation for a new object. Tries the batched
        // EXT_structural_metadata path first (the GLBs produced by cityjson2glb
        // are a single mesh), then falls back to per-mesh name/userData match.
        function startZoomAnimation(id) {
            selectedID = id;
            selectedOBJ = null;
            let activeId = id;
            let attempts = 0;
            const maxAttempts = 3;  // original click + walk one or two child levels

            // Restore previous non-batched material (if any).
            if (previousOBJ && originalMaterials[previousOBJ.uuid]) {
                previousOBJ.material = originalMaterials[previousOBJ.uuid];
                delete originalMaterials[previousOBJ.uuid];
            }
            previousOBJ = null;

            // Clean up previous batched highlight.
            if (currentHighlightMesh) {
                if (currentHighlightMesh.parent) currentHighlightMesh.parent.remove(currentHighlightMesh);
                if (currentHighlightMesh.geometry) currentHighlightMesh.geometry.dispose();
                if (currentHighlightMesh.material) currentHighlightMesh.material.dispose();
                currentHighlightMesh = null;
            }

            // Collect candidate batched objects once — they don't change between retries.
            const batchedCandidates = [];
            scene.traverse(child => {
                if ((child.isMesh || child.isLine || child.isLineSegments || child.isPoints) &&
                    child.geometry && child.geometry.attributes) {
                    const hasFeatureAttr = Object.keys(child.geometry.attributes).some(k =>
                        k.toLowerCase().includes('feature_id') ||
                        k.toLowerCase().includes('batchid') ||
                        k.toLowerCase().includes('objectid')
                    );
                    if (hasFeatureAttr) batchedCandidates.push(child);
                }
            });

            // Retry loop: if the clicked id is a parent CityObject (no direct
            // geometry in the GLB), walk its children for a renderable id.
            while (attempts < maxAttempts) {
                attempts++;
                const match = lookupFeatureId(activeId);  // brace-tolerant

                if (match) {
                    for (const bObj of batchedCandidates) {
                        const highlight = highlightBatchedFeature(bObj, match.fid);
                        if (highlight) {
                            currentHighlightMesh = highlight;
                            selectedOBJ = currentHighlightMesh;
                            activeId = match.id;  // remember which form actually hit
                            break;
                        }
                    }
                }
                if (selectedOBJ) break;

                const fallbackId = findRenderableFallbackID(activeId);
                if (fallbackId && fallbackId !== activeId) {
                    console.log(`"${activeId}" has no triangles; trying child "${fallbackId}"`);
                    activeId = fallbackId;
                    continue;
                }
                break;
            }

            // Fallback: per-mesh lookup for non-batched GLBs.
            if (!selectedOBJ) {
                selectedOBJ = findObjectByNameOrUUID(scene, activeId);
                if (selectedOBJ && selectedOBJ.material) {
                    if (!originalMaterials[selectedOBJ.uuid]) {
                        originalMaterials[selectedOBJ.uuid] = Array.isArray(selectedOBJ.material)
                            ? selectedOBJ.material.map(m => m.clone())
                            : selectedOBJ.material.clone();
                    }
                    const highlightMat = new THREE.MeshStandardMaterial({
                        color: 0xf44336,
                        transparent: false,
                        opacity: 1.0,
                        side: THREE.DoubleSide
                    });
                    selectedOBJ.material = Array.isArray(selectedOBJ.material)
                        ? selectedOBJ.material.map(() => highlightMat)
                        : highlightMat;
                    previousOBJ = selectedOBJ;
                }
            }

            if (selectedOBJ) {
                isAutoZooming = true;
                console.log("Highlighted:", activeId, "(clicked:", id + ")");
            } else {
                console.warn(`Object "${id}" (tried "${activeId}") could not be highlighted (featureIdMap has ${Object.keys(featureIdMap).length} entries).`);
            }
        }

        // The per-item click handler in processJsonData calls _currentStartZoom
        // directly. We just register the latest closure here so repeated
        // "View Full Model" clicks always drive the most recent viewer.
        const uriListEl = document.getElementById("uriList");
        if (uriListEl) uriListEl._currentStartZoom = startZoomAnimation;
    }
});
