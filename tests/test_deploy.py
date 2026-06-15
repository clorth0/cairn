from pathlib import Path

from cairn.config import Config, SiteConfig, BuildConfig, DeployConfig
from cairn.deploy import emit


def cfg(tmp_path, target):
    return Config(
        site=SiteConfig(title="t", url="https://e.com", author="a", description="d"),
        build=BuildConfig(output_dir=str(tmp_path / "public")),
        deploy=DeployConfig(target=target),
    )


def test_github_pages_emits_workflow(tmp_path):
    written = emit(cfg(tmp_path, "github-pages"), project_dir=tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "deploy.yml"
    assert workflow in written
    assert workflow.exists()
    assert "actions/deploy-pages" in workflow.read_text()


def test_cloudflare_emits_headers_note(tmp_path):
    written = emit(cfg(tmp_path, "cloudflare"), project_dir=tmp_path)
    assert any(p.name == "_headers" for p in written)


def test_folder_target_emits_nothing(tmp_path):
    written = emit(cfg(tmp_path, "folder"), project_dir=tmp_path)
    assert written == []
