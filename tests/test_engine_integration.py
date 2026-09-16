import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_NODE = ROOT / "engine" / "node.exe"
ENGINE_CLI = ROOT / "engine" / "kordoc" / "dist" / "cli.js"
SAMPLE_DIR = ROOT / "sample"


def run_engine(source: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="kordoc_test_") as temp_dir:
        output = Path(temp_dir) / f"{source.stem}.md"
        completed = subprocess.run(
            [str(ENGINE_NODE), str(ENGINE_CLI), str(source), "-o", str(output), "--silent"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr or completed.stdout)
        return output.read_text(encoding="utf-8")


class EngineIntegrationTests(unittest.TestCase):
    def test_bundled_engine_is_pinned_to_3_0_0(self):
        if not ENGINE_NODE.exists() or not ENGINE_CLI.exists():
            self.skipTest("로컬 배포 엔진이 없는 소스 전용 환경이야")

        completed = subprocess.run(
            [str(ENGINE_NODE), str(ENGINE_CLI), "--version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=True,
        )
        self.assertEqual(completed.stdout.strip(), "3.0.0")

    def test_numbered_finding_titles_are_restored(self):
        samples = sorted(SAMPLE_DIR.glob("*.hwp")) + sorted(SAMPLE_DIR.glob("*.hwpx"))
        if not samples:
            self.skipTest("통합 테스트용 HWP 또는 HWPX 샘플이 없어")
        if not ENGINE_NODE.exists() or not ENGINE_CLI.exists():
            self.skipTest("로컬 배포 엔진이 없는 소스 전용 환경이야")

        expected_titles = [
            "예산총칙 작성 누락",
            "예산의 초과 집행",
            "결산서 부속명세서 작성 및 공개 누락",
            "미지급금 명세서 작성 미흡",
            "자산관리대장 미작성 등 자산관리 미흡",
            "업무추진비 집행 관리 미흡",
            "학생지원비 집행 관리 미흡",
            "기본재산 소송 관할청 신고 관리 미흡",
            "수익용 기본재산 확보율 기준 미충족",
            "수익용 기본재산 수익률 기준 미충족",
            "학교운영경비 부담 기준 미충족",
        ]

        for sample in samples:
            with self.subTest(sample=sample.name):
                markdown = run_engine(sample)
                restored = re.findall(r"(?m)^(\d+)\) (.+?) \(작성자\s*:\s*.+?\)$", markdown)
                self.assertEqual(
                    restored,
                    [(str(index), title) for index, title in enumerate(expected_titles, start=1)],
                )

    def test_development_uses_repository_engine(self):
        import main

        command = main.KordocParserApp.get_engine_command(object())
        self.assertEqual(command, [str(ENGINE_NODE), str(ENGINE_CLI)])


if __name__ == "__main__":
    unittest.main()
