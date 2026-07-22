from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mapping_mutations_verify_tenant_ownership():
    source = (ROOT / "backend" / "app" / "modules" / "forwarding" / "repository.py").read_text(encoding="utf-8")

    assert source.count("WHERE tenant_id=$1 AND id=$2") >= 2
    assert "mapping_targets" in source


def test_member_mutations_verify_tenant_ownership():
    source = (ROOT / "backend" / "app" / "modules" / "tenants" / "repository.py").read_text(encoding="utf-8")

    assert source.count("WHERE tenant_id=$1 AND id=$2") >= 2
    assert "role<>'owner'" in source
