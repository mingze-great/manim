import json
import asyncio
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"


def test_material_spec_matrix_covers_requested_count_and_matching_fields():
    from app.services.material_library_generation import build_material_specs

    specs = build_material_specs(6)

    assert [item["file_name"] for item in specs] == [f"{index}.png" for index in range(1, 7)]
    assert len({item["emotion_primary"] for item in specs}) >= 4
    assert {"hook", "problem", "method", "result"}.issubset({role for item in specs for role in item["storyboard_roles"]})
    for item in specs:
        assert item["search_keywords"]
        assert item["psychology_concepts"]
        assert item["prompt"]


def test_write_material_manifest_uses_existing_numbered_images(tmp_path):
    from app.services.material_library_generation import build_material_specs, write_material_manifest

    specs = build_material_specs(2)
    (tmp_path / "1.png").write_bytes(b"one")
    (tmp_path / "2.png").write_bytes(b"two")

    manifest_path = write_material_manifest(tmp_path, specs)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest_path.name == "materials.json"
    assert len(payload) == 2
    assert payload[0]["image_path"] == str((tmp_path / "1.png").resolve())


def test_generation_service_stops_after_two_samples_then_builds_library(tmp_path):
    from app.database import Base
    from app.models.material_library_generation import MaterialLibraryGeneration
    from app.services.material_library_generation import MaterialLibraryGenerationService

    engine = create_engine(f"sqlite:///{tmp_path / 'generation.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    generated_root = tmp_path / "generated-images"
    generated_root.mkdir()

    class FakeImageGenerator:
        calls = []

        async def generate_image(self, prompt, reference_images=None):
            index = len(self.calls) + 1
            self.calls.append((prompt, reference_images))
            source = generated_root / f"source-{index}.png"
            source.write_bytes(f"image-{index}".encode())
            return f"/api/article-images/{source.name}", f"/api/article-images/{source.name}", "local"

    output_dir = tmp_path / "library"
    output_dir.mkdir()
    reference = output_dir / "reference.png"
    reference.write_bytes(b"reference")
    job = MaterialLibraryGeneration(
        user_id=1,
        library_key="demo_library",
        library_name="演示素材库",
        target_count=4,
        status="sample_pending",
        reference_image_path=str(reference),
        output_dir=str(output_dir),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    service = MaterialLibraryGenerationService(FakeImageGenerator(), generated_root)
    asyncio.run(service.generate_samples(db, job))

    assert job.status == "samples_ready"
    assert (output_dir / "1.png").exists()
    assert (output_dir / "2.png").exists()
    assert not (output_dir / "3.png").exists()

    asyncio.run(service.generate_batch(db, job))

    assert job.status == "completed"
    assert (output_dir / "4.png").exists()
    assert (output_dir / "materials.json").exists()
    assert len(FakeImageGenerator.calls) == 4


def test_material_library_task_time_limit_covers_maximum_serial_batch():
    from app.tasks.celery_tasks import generate_material_library_celery

    assert generate_material_library_celery.soft_time_limit >= 15000
    assert generate_material_library_celery.time_limit > generate_material_library_celery.soft_time_limit
