
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
            viewWhole(glbUrl);
    
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

        // Function to parse POLYGON Z coordinates
        function parsePolygonZ(polygonZ) {
            return polygonZ
                .replace(/POLYGON Z \(\(|\)\)/g, "") // Remove "POLYGON Z ((" and "))"
                .split(",") // Split into individual coordinates
                .map(coord => {
                    const [x, y, z] = coord.trim().split(/\s+/).map(Number); // Split by spaces and convert to numbers
                    return [x, y, z];
                });
        }

        // Function to normalize coordinates
        function normalizeCoordinates(polygonZs) {
            const allCoords = polygonZs.flatMap(polygonZ => parsePolygonZ(polygonZ));

            // Find min and max values for normalization
            const minX = Math.min(...allCoords.map(coord => coord[0]));
            const maxX = Math.max(...allCoords.map(coord => coord[0]));
            const minY = Math.min(...allCoords.map(coord => coord[1]));
            const maxY = Math.max(...allCoords.map(coord => coord[1]));
            const minZ = Math.min(...allCoords.map(coord => coord[2]));
            const maxZ = Math.max(...allCoords.map(coord => coord[2]));

            // Normalize coordinates to [0, 1] range
            return polygonZs.map(polygonZ =>
                parsePolygonZ(polygonZ).map(([x, y, z]) => [
                    (x - minX) / (maxX - minX || 1), // Avoid division by zero
                    (y - minY) / (maxY - minY || 1),
                    (z - minZ) / (maxZ - minZ || 1),
                ])
            );
        }

        // Function to create a 3D viewer
        function create3DViewer(container, normalizedCoords) {
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(75, container.offsetWidth / container.offsetHeight, 0.1, 1000);
            const renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(container.offsetWidth, container.offsetHeight);
            renderer.shadowMap.enabled = true; // Enable shadows
            renderer.shadowMap.type = THREE.PCFSoftShadowMap; // Soft shadows
            container.appendChild(renderer.domElement);

            // Set a solid bright background color
            renderer.setClearColor(0x87ceeb); // Sky blue color

            // Add lighting
            const ambientLight = new THREE.AmbientLight(0x404040); // Soft white light
            scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
            directionalLight.position.set(5, 5, 5).normalize();
            directionalLight.castShadow = true; // Enable shadows for this light
            scene.add(directionalLight);

            // Create a mesh for each polygon
            normalizedCoords.forEach(coords => {
                const vertices = new Float32Array(coords.flat());
                if (vertices.some(isNaN)) {
                    console.error("Invalid vertices detected:", vertices);
                    return; // Skip invalid polygons
                }

                const geometry = new THREE.BufferGeometry();
                geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));

                // Compute normals for the geometry
                geometry.computeVertexNormals();

                const material = new THREE.MeshPhongMaterial({
                    color: 0x808080, // Gray color
                    shininess: 100, // Metallic shine
                    side: THREE.DoubleSide
                });
                const mesh = new THREE.Mesh(geometry, material);
                mesh.castShadow = true; // Enable shadows for this mesh
                mesh.receiveShadow = true; // Allow this mesh to receive shadows
                scene.add(mesh);
            });

            // Position the camera
            camera.position.set(2, 2, 2);
            camera.lookAt(0, 0, 0);

            // Add orbit controls for zoom and rotate
            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true; // Smooth controls
            controls.dampingFactor = 0.25;

            // Disable left-click interaction with OrbitControls
            controls.mouseButtons = {
                LEFT: null, // Disable left-click
                MIDDLE: THREE.MOUSE.DOLLY, // Middle-click for zoom
                RIGHT: THREE.MOUSE.ROTATE // Right-click for rotation
            };

            // Animation loop
            function animate() {
                requestAnimationFrame(animate);
                controls.update(); // Required for damping
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

                // Track whether the viewer is open
                let isViewerOpen = false;

                // Add click event to toggle 3D viewer visibility
                listItem.addEventListener("click", () => {
                    if (isViewerOpen) {
                        viewerContainer.classList.remove("visible");
                        viewerContainer.innerHTML = ""; // Clear the viewer
                        isViewerOpen = false;
                    } else {
                        viewerContainer.classList.add("visible");
                        const normalizedCoords = normalizeCoordinates(jsonData[objectURI]);
                        create3DViewer(viewerContainer, normalizedCoords);
                        isViewerOpen = true;
                        selectedID = listItem.textContent.split("#")[1];
                        console.log(selectedID);
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
    
    function viewWhole(glbdata) {
        const container = document.getElementById('displayContent');
    
        // Initialize scene, camera, and renderer
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(
            75,
            container.offsetWidth / container.offsetHeight,
            0.1,
            1000
        );
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
    
        // Function to find an object by name or UUID
        function findObjectByNameOrUUID(model, id) {
            let targetObject = null;
            model.traverse((child) => {
                if (child.name === id || child.uuid === id) {
                    targetObject = child;
                }
                else if (child.name.includes(id) || child.uuid.includes(id)) {
                    targetObject = child;
                }
            });
            return targetObject;
        }
    
        // Load the GLB model
        const loader = new THREE.GLTFLoader();
        loader.load(
            glbdata,
            function (gltf) {
                const model = gltf.scene;
                scene.add(model);
    
                // Center and scale the model
                model.scale.set(0.1, 0.1, 0.1);
                const box = new THREE.Box3().setFromObject(model);
                const center = box.getCenter(new THREE.Vector3());
                model.position.sub(center);
    
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
    
        // Set up the camera position
        camera.position.z = 10;
    
        // Add OrbitControls for interactivity
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.screenSpacePanning = false;
        controls.minDistance = 1;
        controls.maxDistance = 1000;
    
        // Track zoom-in state
        let isAutoZooming = false; // Flag to control automatic zoom behavior
        let previousOBJ = null; // Store the previously selected object
        let originalMaterials = {}; // Store original materials for restoration
    
        // Animation loop
        function animate() {
            requestAnimationFrame(animate);
    
            // Update controls (if damping is enabled)
            controls.update();
    
            // Rotate the model (optional)
            if (scene.children[0]) {
                scene.children[0].rotation.y += 0.01;
            }
    
            // Perform zoom-in animation if isAutoZooming is true
            if (selectedOBJ && isAutoZooming) {
                // Define the zoom behavior
                const zoomSpeed = 0.05; // Adjust this value for faster/slower zoom
                const minDistance = 5; // Minimum distance from the object
                const maxDistance = 100; // Maximum distance from the object
                const angleOffset = Math.PI / 6; // Angle offset (30 degrees in radians)
    
                // Calculate the bounding box of the selected object
                const boundingBox = new THREE.Box3().setFromObject(selectedOBJ);
                const center = boundingBox.getCenter(new THREE.Vector3());
    
                // Set the controls' target to the object's center
                controls.target.copy(center);
    
                // Adjust the camera's distance to the object
                const currentDistance = camera.position.distanceTo(center);
                let targetDistance = currentDistance - zoomSpeed;
    
                // Clamp the distance to ensure it stays within the min/max range
                targetDistance = Math.max(minDistance, Math.min(maxDistance, targetDistance));
    
                // Stop auto-zooming once the minimum distance is reached
                if (currentDistance <= minDistance) {
                    isAutoZooming = false; // Disable automatic zoom
                }
    
                // Calculate the new camera position with an angle offset
                const direction = center.clone().sub(camera.position).normalize(); // Direction vector from camera to object
                const horizontalPosition = direction.clone().multiplyScalar(targetDistance); // Horizontal position
                const verticalOffset = new THREE.Vector3(0, Math.sin(angleOffset) * targetDistance, 0); // Vertical offset
                const newPosition = center.clone().add(horizontalPosition).add(verticalOffset); // Final position
    
                // Move the camera towards the new position
                camera.position.lerp(newPosition, 0.1); // Smoothing factor
    
                // Ensure the camera looks at the object
                camera.lookAt(controls.target);
            }
    
            // Render the scene
            renderer.render(scene, camera);
        }
    
        // Function to start zoom animation for a new object
        function startZoomAnimation(id) {
            // Restore the previous object's material if it exists
            if (previousOBJ && originalMaterials[previousOBJ.uuid]) {
                previousOBJ.material = originalMaterials[previousOBJ.uuid]; // Restore the original material
                delete originalMaterials[previousOBJ.uuid]; // Remove from storage
            }
    
            // Find the new selected object
            selectedID = id;
            selectedOBJ = findObjectByNameOrUUID(scene, selectedID);
    
            if (selectedOBJ) {
                // Store the original material of the new selected object
                if (!originalMaterials[selectedOBJ.uuid]) {
                    originalMaterials[selectedOBJ.uuid] = selectedOBJ.material.clone(); // Clone the original material
                }
    
                // Apply a temporary material for the selected object
                selectedOBJ.material = new THREE.MeshStandardMaterial({
                    color: 0xff0000, // Example: Red color
                    transparent: true,
                    opacity: 0.5 // Semi-transparent during zoom
                });
    
                // Reset the previous object reference
                previousOBJ = selectedOBJ;
    
                // Start the zoom-in animation
                isAutoZooming = true;
                console.log("Starting zoom-in animation for:", selectedID);
            } else {
                console.warn(`Object with ID "${selectedID}" not found.`);
            }
        }
    
        // Example: Trigger zoom-in animation when a URI is clicked
        document.getElementById("uriList").addEventListener("click", function (event) {
            if (event.target.tagName === "LI") {
                const id = event.target.textContent.split("#")[1]; // Extract the ID from the clicked URI
                startZoomAnimation(id); // Start the zoom animation for the selected ID
            }
        });
    }
});
