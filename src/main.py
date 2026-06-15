import os
import json
import re
import cv2
import fiftyone as fo

# ============================================================
# CONFIG
# ============================================================

from pathlib import Path

ROOT = Path(__file__).parent

images_dir = ROOT / "../data/images"
anno_path = ROOT / "../data/datumaro.json"

dataset_name = "sam3_lora_datumaro_dataset"

# ============================================================
# LOAD DATUMARO JSON
# ============================================================

with open(anno_path, "r") as f:
    datum_data = json.load(f)

# ============================================================
# LABEL MAPPING
# ============================================================

categories = (
    datum_data
    .get("categories", {})
    .get("label", {})
    .get("labels", [])
)

labels_map = {
    idx: cat["name"]
    for idx, cat in enumerate(categories)
}

print("Labels:")
for k, v in labels_map.items():
    print(k, v)

# ============================================================
# CREATE DATASET
# ============================================================

if dataset_name in fo.list_datasets():
    fo.delete_dataset(dataset_name)

dataset = fo.Dataset(dataset_name)

# ============================================================
# LOAD SKELETON DEFINITIONS
# ============================================================

skeletons = {}
label_to_keypoint_field = {}


def _to_field_name(label_name):
    slug = re.sub(r"[^a-z0-9]+", "_", label_name.lower()).strip("_")
    return f"keypoints_{slug}" if slug else "keypoints_unknown"

points_categories = (
    datum_data
    .get("categories", {})
    .get("points", {})
    .get("items", [])
)

for pt_cat in points_categories:

    label_id = pt_cat["label_id"]

    label_name = labels_map.get(label_id)

    if label_name is None:
        continue

    point_labels = pt_cat.get("labels", [])

    datumaro_edges = pt_cat.get("joints", [])

    edges = []

    for edge in datumaro_edges:

        if len(edge) != 2:
            continue

        a, b = edge

        # ------------------------------------------------
        # Datumaro datasets đôi khi export 1-based index
        # ------------------------------------------------

        # if max(a, b) >= len(point_labels):
        #     a -= 1
        #     b -= 1

        edges.append([a - 1, b - 1])

    field_name = _to_field_name(label_name)
    label_to_keypoint_field[label_name] = field_name

    skeletons[field_name] = fo.KeypointSkeleton(
        labels=point_labels,
        edges=edges
    )

dataset.skeletons = skeletons

print("\nLoaded skeletons:")
for field_name, sk in skeletons.items():
    print(
        field_name,
        f"{len(sk.labels)} pts",
        f"{len(sk.edges)} edges"
    )

# ============================================================
# HELPER
# ============================================================

def get_visibility_from_element(element):
    """
    Convert Datumaro point attributes
    -> COCO visibility style

    0 = not labeled
    1 = labeled but occluded
    2 = visible
    """

    attrs = {}

    for a in element.get("attributes", []):
        attrs[a["name"]] = a["value"]

    occluded = attrs.get("occluded", False)

    if isinstance(occluded, str):
        occluded = occluded.lower() == "true"

    return 1 if occluded else 2

# ============================================================
# LOAD SAMPLES
# ============================================================

samples = []

items = datum_data.get("items", [])

for item in items:

    img_id = item["id"]

    image_info = item.get("image", {})

    img_filename = image_info.get("path", "")

    if not img_filename:
        img_filename = img_id + ".jpg"

    img_path = images_dir / os.path.basename(img_filename)

    if not img_path.exists():

        found = False

        for ext in [".jpg", ".jpeg", ".png"]:

            candidate = images_dir / (img_id + ext)

            if candidate.exists():
                img_path = candidate
                found = True
                break

        if not found:
            print("Missing image:", img_id)
            continue

    img = cv2.imread(str(img_path))

    if img is None:
        print("Cannot read:", img_path)
        continue

    height, width = img.shape[:2]

    sample = fo.Sample(filepath=img_path)

    detections = []
    polylines = []
    keypoints_by_field = {}

    # =====================================================
    # ANNOTATIONS
    # =====================================================

    for ann in item.get("annotations", []):

        label = labels_map.get(
            ann.get("label_id"),
            "unknown"
        )

        ann_type = ann["type"]

        # =================================================
        # BBOX
        # =================================================

        if ann_type == "bbox":

            x, y, w, h = ann["bbox"]

            rel_box = [
                x / width,
                y / height,
                w / width,
                h / height
            ]

            detections.append(
                fo.Detection(
                    label=label,
                    bounding_box=rel_box
                )
            )

        # =================================================
        # POLYGON
        # =================================================

        elif ann_type == "polygon":

            pts = ann["points"]

            poly_pts = []

            for i in range(0, len(pts), 2):

                px = pts[i] / width
                py = pts[i + 1] / height

                poly_pts.append((px, py))

            polylines.append(
                fo.Polyline(
                    label=label,
                    points=[poly_pts],
                    closed=True,
                    filled=True
                )
            )

        # =================================================
        # SKELETON / KEYPOINTS
        # =================================================

        elif ann_type == "skeleton":

            kp_points = []
            visibility = []

            # ---------------------------------------------
            # Datumaro skeleton elements
            # ---------------------------------------------

            if "elements" in ann:

                for element in ann["elements"]:

                    if element.get("type") != "points":
                        continue

                    pts = element.get("points", [])

                    if len(pts) < 2:
                        continue

                    x = pts[0] / width
                    y = pts[1] / height

                    kp_points.append((x, y))

                    visibility.append(
                        get_visibility_from_element(
                            element
                        )
                    )

            # ---------------------------------------------
            # Fallback
            # ---------------------------------------------

            elif "points" in ann:

                pts = ann["points"]

                stride = (
                    3
                    if len(pts) % 3 == 0
                    else 2
                )

                for i in range(
                    0,
                    len(pts),
                    stride
                ):

                    x = pts[i] / width
                    y = pts[i + 1] / height

                    kp_points.append((x, y))

                    if stride == 3:
                        visibility.append(
                            int(pts[i + 2])
                        )
                    else:
                        visibility.append(2)

            kp = fo.Keypoint(
                label=label,
                points=kp_points
            )

            kp["visibility"] = visibility

            field_name = label_to_keypoint_field.get(label)

            if field_name and field_name in skeletons:
                kp["point_labels"] = (
                    skeletons[field_name].labels
                )
                keypoints_by_field.setdefault(
                    field_name,
                    []
                ).append(kp)

    # =====================================================
    # SAVE TO SAMPLE
    # =====================================================

    if detections:
        sample["detections"] = fo.Detections(
            detections=detections
        )

    if polylines:
        sample["polygons"] = fo.Polylines(
            polylines=polylines
        )

    for field_name, keypoints in keypoints_by_field.items():
        sample[field_name] = fo.Keypoints(
            keypoints=keypoints
        )

    samples.append(sample)

# ============================================================
# ADD TO DATASET
# ============================================================

dataset.add_samples(samples)

dataset.compute_metadata()

dataset.save()

print(
    f"\nSuccessfully loaded {len(dataset)} samples"
)

# ============================================================
# DEBUG
# ============================================================

print("\nSkeleton definitions:")

for name, sk in dataset.skeletons.items():

    print(
        f"{name}: "
        f"{len(sk.labels)} pts, "
        f"{len(sk.edges)} edges"
    )

# ============================================================
# OPEN APP
# ============================================================

session = fo.launch_app(dataset)
session.wait()
# print(dataset.skeletons)