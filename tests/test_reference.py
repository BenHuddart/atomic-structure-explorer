from atomic_structure_explorer.reference import ReferenceRepository


def test_only_verified_reference_data_can_be_loaded():
    repository = ReferenceRepository()
    assert repository.manifest["schema_version"] == 1
    assert repository.datasets() == ()
