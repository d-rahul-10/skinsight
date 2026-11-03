from pathlib import Path

from build_manifest import build_manifest, class_label_from_directory


def test_class_label_removes_numbering_and_image_count_suffixes() -> None:
    assert class_label_from_directory("1. Eczema 1677") == "Eczema"
    assert class_label_from_directory("3. Atopic Dermatitis - 1.25k") == "Atopic Dermatitis"
    assert class_label_from_directory("10. Warts and Viral Infections - 2103") == "Warts and Viral Infections"


def test_build_manifest_collects_images_from_class_folders(tmp_path: Path) -> None:
    data_root = tmp_path / "IMG_CLASSES"
    (data_root / "1. Eczema 1677").mkdir(parents=True)
    (data_root / "2. Melanoma 15.75k").mkdir()
    (data_root / "1. Eczema 1677" / "nested").mkdir()
    (data_root / "1. Eczema 1677" / "a.jpg").touch()
    (data_root / "1. Eczema 1677" / "nested" / "b.png").touch()
    (data_root / "2. Melanoma 15.75k" / "c.webp").touch()
    (data_root / "2. Melanoma 15.75k" / "ignored.txt").touch()

    output = tmp_path / "manifest.csv"
    counts = build_manifest(data_root, output)

    assert counts == {"Eczema": 2, "Melanoma": 1}
    contents = output.read_text(encoding="utf-8")
    assert "image,label" in contents
    assert "a.jpg,Eczema" in contents
    assert "c.webp,Melanoma" in contents
    assert "ignored.txt" not in contents
