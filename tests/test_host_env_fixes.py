import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure src/ is on sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import osdoc
from engine.transcription import TranscriptionMixin


class DummyTranscriptionEngine(TranscriptionMixin):
    def __init__(self, doc):
        self.os_doc = doc
        self.models_dir = os.path.join(doc.install_dir, "models")
        self.libs_dir = os.path.join(doc.install_dir, "libs")


class TestHostEnvFixes(unittest.TestCase):
    """
    Regression test suite for cross-platform hardware, environment,
    script sync, and runtime stability fixes.
    """

    def setUp(self):
        self.doc = osdoc.OSDoctor()
        self.engine = DummyTranscriptionEngine(self.doc)

    def test_davinci_wrapper_content_valid_syntax(self):
        """
        Verify generate_davinci_wrapper_content runs without NameError ('_host_ver')
        and outputs syntactically valid Python code.
        """
        content = self.doc.generate_davinci_wrapper_content()
        self.assertIsInstance(content, str)
        self.assertIn("[BadWords] Host Python (", content)
        # Verify valid Python syntax in the generated wrapper
        compiled = compile(content, "BadWords.py", "exec")
        self.assertIsNotNone(compiled)

    def test_has_nvidia_support_rejects_old_drivers(self):
        """
        Verify has_nvidia_support rejects older NVIDIA drivers (< 525)
        to prevent CUDA 12 runtime crashes on Kepler GPUs.
        """
        # Mock nvidia-smi query output for an old Kepler driver (456.71)
        mock_res_old = MagicMock()
        mock_res_old.stdout = "456.71\n"
        mock_res_old.returncode = 0

        with patch("subprocess.run", return_value=mock_res_old):
            supported = self.doc.has_nvidia_support()
            self.assertFalse(supported, "Driver 456.71 must be rejected (< 525 required for CUDA 12).")

        # Mock nvidia-smi query output for a modern driver (535.104)
        mock_res_new = MagicMock()
        mock_res_new.stdout = "535.104.05\n"
        mock_res_new.returncode = 0

        with patch("subprocess.run", return_value=mock_res_new):
            with patch.object(self.doc, "is_win", True):
                supported = self.doc.has_nvidia_support()
                self.assertTrue(supported, "Driver >= 525 on Windows must be accepted.")

    def test_compute_cap_query_failure_handling(self):
        """
        Verify _get_optimal_compute_type does not crash with ValueError when
        nvidia-smi outputs an error message ending with a dot.
        """
        mock_res = MagicMock()
        mock_res.stdout = 'Field "compute_cap" is not a valid field to query.\n'
        mock_res.returncode = 0

        with patch("subprocess.run", return_value=mock_res):
            comp_type = self.engine._get_optimal_compute_type(device="cuda")
            self.assertIn(comp_type, ("int8", "int8_float32"))

    def test_cuda_preinit_code_disabled_on_cpu(self):
        """
        Verify that _get_cuda_preinit_code produces an empty string for CPU mode
        to prevent unauthorized / crashing CUDA DLL loads on legacy hardware.
        """
        cpu_code = self.engine._get_cuda_preinit_code(fw_device="cpu")
        self.assertEqual(cpu_code.strip(), "", "CUDA preinit must be completely empty on CPU.")

        cuda_code = self.engine._get_cuda_preinit_code(fw_device="cuda")
        self.assertIn("NVIDIA CUDA", cuda_code)
        # Verify dangerous blind ctypes.CDLL loop is removed
        self.assertNotIn("ctypes.CDLL(os.path.join(_d, _f))", cuda_code)

    def test_get_short_path_graceful_fallback(self):
        """
        Verify get_short_path returns the original path gracefully on non-Windows
        or non-existent paths.
        """
        test_path = "/non/existent/path/with spaces/test.py"
        res = self.doc.get_short_path(test_path)
        self.assertEqual(res, test_path)

    def test_is_cuda_functional_handles_non_cuda_device(self):
        """
        Verify is_cuda_functional returns (False, reason) when no CUDA device is usable.
        """
        mock_res = MagicMock()
        mock_res.stdout = "NO_CUDA_DEVICES\n"
        mock_res.returncode = 2

        with patch("subprocess.run", return_value=mock_res):
            usable, reason = self.engine.is_cuda_functional()
            self.assertFalse(usable)
            self.assertIn("NO_CUDA_DEVICES", reason)


if __name__ == "__main__":
    unittest.main()
