package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"io"
	"os"
	"strconv"
	"strings"
	"testing"
)

const fixtureResource = "fixture-resource\n"

func validRequest(t *testing.T, operation string) []byte {
	t.Helper()
	digest := sha256.Sum256([]byte(fixtureResource))
	digestText := "sha256:" + hex.EncodeToString(digest[:])
	request := map[string]any{
		"schema_version": "1.0",
		"input": map[string]any{
			"schema_version": "1.0",
			"standard_id":    fixtureStandard,
			"version":        fixtureVersion,
			"operation":      operation,
			"config":         map[string]any{},
			"resources":      map[string]string{resourceID: digestText},
			"snapshots":      map[string]any{"fixture": "input"},
		},
		"resources": map[string]string{
			resourceID: base64.StdEncoding.EncodeToString([]byte(fixtureResource)),
		},
	}
	encoded, err := json.Marshal(request)
	if err != nil {
		t.Fatalf("json.Marshal(valid request) error = %v, want nil", err)
	}
	return encoded
}

func TestExecuteSupportsEveryFixtureOperation(t *testing.T) {
	for _, operation := range []string{"render", "validate", "verify", "drift-check"} {
		t.Run(operation, func(t *testing.T) {
			request, input, err := decodeRequest(bytes.NewReader(validRequest(t, operation)))
			if err != nil {
				t.Fatalf("decodeRequest(%q) error = %v, want nil", operation, err)
			}
			got, err := execute(request, input)
			if err != nil {
				t.Fatalf("execute(%q) error = %v, want nil", operation, err)
			}
			if got.Observed.Operation != operation {
				t.Errorf("execute(%q).Observed.Operation = %q, want %q", operation, got.Observed.Operation, operation)
			}
			if operation == "render" && !strings.Contains(got.Content, fixtureResource) {
				t.Errorf("execute(%q).Content = %q, want resource %q", operation, got.Content, fixtureResource)
			}
			if operation != "render" && len(got.Findings) != 1 {
				t.Errorf("execute(%q).Findings length = %d, want 1", operation, len(got.Findings))
			}
		})
	}
}

func TestDecodeRequestRejectsHollowOrMalformedTransport(t *testing.T) {
	tests := map[string][]byte{
		"non-object":       []byte(`[]`),
		"unknown-field":    append(validRequest(t, "render")[:len(validRequest(t, "render"))-1], []byte(`,"extra":true}`)...),
		"trailing-object":  append(validRequest(t, "render"), []byte(`{}`)...),
		"missing-resource": []byte(`{"schema_version":"1.0","input":{},"resources":{}}`),
	}
	for name, request := range tests {
		t.Run(name, func(t *testing.T) {
			if _, _, err := decodeRequest(bytes.NewReader(request)); err == nil {
				t.Errorf("decodeRequest(%s) error = nil, want rejection", name)
			}
		})
	}
}

func TestRunWritesOnlyTheInheritedResultDescriptor(t *testing.T) {
	resultRead, resultWrite, err := os.Pipe()
	if err != nil {
		t.Fatalf("os.Pipe() error = %v, want nil", err)
	}
	t.Cleanup(func() {
		if err := resultRead.Close(); err != nil {
			t.Errorf("resultRead.Close() error = %v, want nil", err)
		}
	})

	args := []string{"command-provider-fixture", strconv.Itoa(int(resultWrite.Fd()))}
	if err := run(args, bytes.NewReader(validRequest(t, "render"))); err != nil {
		t.Fatalf("run(valid request) error = %v, want nil", err)
	}
	result, err := io.ReadAll(resultRead)
	if err != nil {
		t.Fatalf("io.ReadAll(result descriptor) error = %v, want nil", err)
	}
	var decoded providerResult
	if err := json.Unmarshal(result, &decoded); err != nil {
		t.Fatalf("json.Unmarshal(result) error = %v, want nil", err)
	}
	if decoded.Observed.Operation != "render" {
		t.Errorf("run(valid request) operation = %q, want render", decoded.Observed.Operation)
	}
}
