package render

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

const priorBytes = "# prior ledger\n\nContent a failed refresh must not destroy.\n"

func seedLedger(t *testing.T) string {
	t.Helper()

	path := filepath.Join(t.TempDir(), "docs", "GH-WORKFLOWS.md")
	if err := os.MkdirAll(filepath.Dir(path), 0o750); err != nil {
		t.Fatalf("MkdirAll error = %v", err)
	}
	if err := os.WriteFile(path, []byte(priorBytes), 0o600); err != nil {
		t.Fatalf("WriteFile error = %v", err)
	}
	return path
}

func readBack(t *testing.T, path string) string {
	t.Helper()
	// #nosec G304 G703 -- the path is this test's own temporary directory.
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile(%s) error = %v", path, err)
	}
	return string(data)
}

// assertNoResidue proves the failure path cleans up after itself: a directory left
// holding temp files would turn every failed refresh into repository litter.
func assertNoResidue(t *testing.T, path string) {
	t.Helper()

	entries, err := os.ReadDir(filepath.Dir(path))
	if err != nil {
		t.Fatalf("ReadDir error = %v", err)
	}
	for _, entry := range entries {
		if entry.Name() != filepath.Base(path) {
			t.Errorf("failed write left %q behind", entry.Name())
		}
	}
}

func TestWriteAtomicReplacesTheWholeFile(t *testing.T) {
	t.Parallel()

	path := seedLedger(t)
	const next = "# next ledger\n"
	if err := WriteAtomic(path, []byte(next)); err != nil {
		t.Fatalf("WriteAtomic() error = %v", err)
	}
	if got := readBack(t, path); got != next {
		t.Errorf("file = %q, want %q", got, next)
	}
	assertNoResidue(t, path)
}

func TestWriteAtomicCreatesTheFileAndItsDirectory(t *testing.T) {
	t.Parallel()

	path := filepath.Join(t.TempDir(), "docs", "GH-WORKFLOWS.md")
	if err := WriteAtomic(path, []byte("# new\n")); err != nil {
		t.Fatalf("WriteAtomic() error = %v", err)
	}
	if got := readBack(t, path); got != "# new\n" {
		t.Errorf("file = %q", got)
	}
}

// DR-003 makes the ledger tool-owned whole-file content, which is only safe if a failed
// refresh is invisible: the operator must never be left with half a ledger.
func TestWriteAtomicPreservesPriorBytesWhenTheWriteFails(t *testing.T) {
	t.Parallel()

	path := seedLedger(t)
	injected := errors.New("injected write failure")

	err := writeAtomic(path, []byte("# replacement that must never land\n"),
		func(*os.File, []byte) error { return injected })
	if !errors.Is(err, injected) {
		t.Fatalf("writeAtomic() error = %v, want the injected failure", err)
	}
	if got := readBack(t, path); got != priorBytes {
		t.Errorf("prior bytes were damaged by a failed write:\n%s", got)
	}
	assertNoResidue(t, path)
}

func TestWriteAtomicPreservesPriorBytesWhenTheDirectoryIsUnwritable(t *testing.T) {
	t.Parallel()

	if os.Geteuid() == 0 {
		t.Skip("root ignores directory permissions")
	}
	path := seedLedger(t)
	dir := filepath.Dir(path)
	// #nosec G302 -- making the directory unwritable is the failure being injected.
	if err := os.Chmod(dir, 0o500); err != nil {
		t.Fatalf("Chmod error = %v", err)
	}
	// #nosec G302 -- restored so the test framework can clean the directory up.
	t.Cleanup(func() { _ = os.Chmod(dir, 0o700) })

	if err := WriteAtomic(path, []byte("# replacement that must never land\n")); err == nil {
		t.Fatal("WriteAtomic() error = nil, want a failure on an unwritable directory")
	}
	if got := readBack(t, path); got != priorBytes {
		t.Errorf("prior bytes were damaged by a failed write:\n%s", got)
	}
}
