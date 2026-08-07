package render

import (
	"fmt"
	"os"
	"path/filepath"
)

// ledgerFileMode is the mode a freshly created ledger gets: ordinary readable repository
// content, matching what a checkout of a committed file would produce. An existing
// file's mode is preserved instead.
const ledgerFileMode os.FileMode = 0o644

// WriteAtomic replaces a file's entire contents, or leaves it exactly as it was.
//
// The ledger is tool-owned whole-file content (spec DR-003) that is regenerated rather
// than merged, so a partial write is worse than no write at all: the operator would be
// left with a document that looks current and is not. Every failure path here — the temp
// file, the write, the sync, the rename — leaves the previous bytes untouched, and the
// temp file is removed rather than left as repository litter.
func WriteAtomic(path string, data []byte) error {
	return writeAtomic(path, data, writeAll)
}

// writeAtomic carries the write step as a parameter so a failure mid-write can be
// injected in tests. A partial write is the failure the atomicity guarantee exists for,
// and it is unreachable through the exported API.
func writeAtomic(path string, data []byte, write func(*os.File, []byte) error) (err error) {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o750); err != nil {
		return fmt.Errorf("creating %s: %w", dir, err)
	}

	mode := ledgerFileMode
	if info, statErr := os.Stat(path); statErr == nil {
		mode = info.Mode().Perm()
	}

	// The temp file is created in the destination directory because rename is only
	// atomic within a filesystem, and /tmp is routinely a different one.
	temp, err := os.CreateTemp(dir, ".gh-workflow-*.tmp")
	if err != nil {
		return fmt.Errorf("creating a temporary file in %s: %w", dir, err)
	}
	tempPath := temp.Name()
	defer func() {
		if err != nil {
			_ = temp.Close()
			_ = os.Remove(tempPath)
		}
	}()

	if err = write(temp, data); err != nil {
		return fmt.Errorf("writing %s: %w", tempPath, err)
	}
	// Durability before visibility: a rename that beats its own data to disk can survive
	// a crash as an empty file, which is the partial state this function exists to
	// prevent.
	if err = temp.Sync(); err != nil {
		return fmt.Errorf("flushing %s: %w", tempPath, err)
	}
	if err = temp.Close(); err != nil {
		return fmt.Errorf("closing %s: %w", tempPath, err)
	}
	// #nosec G302 -- generated repository documentation is world-readable content, not a
	// secret; the mode matches what checking the file out of Git would produce.
	if err = os.Chmod(tempPath, mode); err != nil {
		return fmt.Errorf("setting the mode of %s: %w", tempPath, err)
	}
	if err = os.Rename(tempPath, path); err != nil {
		return fmt.Errorf("replacing %s: %w", path, err)
	}
	return nil
}

func writeAll(f *os.File, data []byte) error {
	_, err := f.Write(data)
	return err
}
