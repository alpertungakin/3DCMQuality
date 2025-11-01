## **The repository of "[Leveraging Knowledge Graphs and Semantic Web Technologies for Validating 3D City Models](https://doi.org/10.1080/13658816.2025.2578723)"**

***Prerequisites***

* [Anaconda](https://www.anaconda.com/) or Miniconda

## Installation

```bash
# Fetch the repo
git clone https://github.com/alpertungakin/3DCMQuality.git
cd 3DCMQuality/Valid_app_gui
# Create & activate the Conda environment
conda env create -f environment.yml
conda activate validation3d
```

## Run the application

```bash
python app.py
```

The Flask server starts at **[http://127.0.0.1:5000](http://127.0.0.1:5000)**.


## Using the Interface

1. **Select an ontology** – choose **“Validation ontology based on QIE 2016.”**
2. **Upload a CityJSON file** – sample data live in the `cityjson/` folder.
3. **View the full model** – click ***View Full Model***.
4. **Run validation** – click ***Process Data*** (bottom‑left).
   Processing time scales with model size and your hardware.
5. **Inspect results**

   * **Download** the validation report (`*.ttl`).
   * Open ***Validation Results Interface***, upload the report, and browse invalidities grouped by *Source Shape* or *individuals*.
   * Click ***Visual Objects*** to list invalid geometries; selecting an item highlights it in the full‑model view.

---

## Reproducing Table 5 (Violation Percantages)

With the `validation3d` environment active:

```bash
python violations_summary_concerngranules.py
```

When prompted, enter the object totals below, after selecting the report file the application generated:

| City Model | Solids | Surfaces |
| ---------- | -----: | -------: |
| Den Haag   |  1 990 |   16 209 |
| Rotterdam  |    853 |   15 482 |
| Vienna     |  2 204 |   43 260 |

---

## Troubleshooting

| Symptom                                           | Fix                                                                                    |
| ------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **Chrome tab crashes**                            | Clear cache or use Firefox/Edge.                                                       |
| **`ModuleNotFoundError`**                             | Ensure the Conda env is active: `conda activate validation3d`.                         |

---

## License & Citation

This repository is distributed under the **CC BY-NC 4.0** license.
You may use the code for academic and research purposes with proper citation.
Commercial use requires prior permission from the author.

```bibtex
@article{akın_usta_stoter_arroyo ohori_cömert_2025, title={Leveraging knowledge graphs and semantic web technologies for validating 3D city models}, ISSN={1365-8816}, DOI={10.1080/13658816.2025.2578723}, journal={International Journal of Geographical Information Science}, publisher={International Journal of Geographical Information Science}, author={Akın, Alper Tunga and Usta, Ziya and Stoter, Jantien and Arroyo Ohori, Ken and Cömert, Çetin}, year={2025}, pages={1–27} }
.
```
