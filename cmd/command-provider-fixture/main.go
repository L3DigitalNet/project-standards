// Command command-provider-fixture implements the frozen command-provider wire ABI.
//
// It is a synthetic acceptance artifact, not a production provider. The parent supplies
// one strict JSON request on stdin and appends the inherited result descriptor as
// argv[1]. Stdout and stderr are diagnostics only; successful results are written solely
// to that descriptor.
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"strconv"
)

const (
	fixtureStandard = "command-provider-fixture"
	fixtureVersion  = "1.0"
	resourceID      = "fixture-data"
)

type wireRequest struct {
	SchemaVersion string            `json:"schema_version"`
	Input         json.RawMessage   `json:"input"`
	Resources     map[string]string `json:"resources"`
}

type providerInput struct {
	SchemaVersion string                     `json:"schema_version"`
	StandardID    string                     `json:"standard_id"`
	Version       string                     `json:"version"`
	Operation     string                     `json:"operation"`
	Config        map[string]json.RawMessage `json:"config"`
	Resources     map[string]string          `json:"resources"`
	Snapshots     map[string]json.RawMessage `json:"snapshots"`
}

type observedResult struct {
	SchemaVersion  string                     `json:"schema_version"`
	StandardID     string                     `json:"standard_id"`
	Version        string                     `json:"version"`
	Operation      string                     `json:"operation"`
	ResourceBase64 string                     `json:"resource_base64"`
	ResourceDigest string                     `json:"resource_digest"`
	Snapshots      map[string]json.RawMessage `json:"snapshots"`
	Environment    []string                   `json:"environment"`
}

type finding struct {
	Code     string `json:"code"`
	Severity string `json:"severity"`
	Path     string `json:"path"`
	Identity string `json:"identity"`
	Message  string `json:"message"`
	Hint     string `json:"hint"`
}

type providerResult struct {
	Content  string         `json:"content,omitempty"`
	Findings []finding      `json:"findings,omitempty"`
	Observed observedResult `json:"observed"`
}

func main() {
	if err := run(os.Args, os.Stdin); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(args []string, stdin io.Reader) error {
	if len(args) != 2 {
		return errors.New("command provider requires exactly one result descriptor")
	}
	descriptor, err := strconv.ParseUint(args[1], 10, 64)
	if err != nil || descriptor == 0 {
		return errors.New("command provider result descriptor is invalid")
	}

	request, input, err := decodeRequest(stdin)
	if err != nil {
		return err
	}
	result, err := execute(request, input)
	if err != nil {
		return err
	}
	encoded, err := json.Marshal(result)
	if err != nil {
		return fmt.Errorf("encode provider result: %w", err)
	}

	// The descriptor is the only result channel. Writing the same object to stdout
	// would turn a plausible diagnostic-only transport into a false-positive fixture.
	resultFile := os.NewFile(uintptr(descriptor), "provider-result")
	if resultFile == nil {
		return errors.New("command provider result descriptor is unavailable")
	}
	if _, err := resultFile.Write(encoded); err != nil {
		_ = resultFile.Close()
		return fmt.Errorf("write provider result: %w", err)
	}
	if err := resultFile.Close(); err != nil {
		return fmt.Errorf("close provider result: %w", err)
	}
	return nil
}

func decodeRequest(stdin io.Reader) (wireRequest, providerInput, error) {
	var request wireRequest
	if err := decodeStrict(stdin, &request); err != nil {
		return wireRequest{}, providerInput{}, fmt.Errorf("decode command request: %w", err)
	}
	if request.SchemaVersion != "1.0" {
		return wireRequest{}, providerInput{}, errors.New("unsupported command request schema")
	}

	var input providerInput
	if err := decodeStrict(bytes.NewReader(request.Input), &input); err != nil {
		return wireRequest{}, providerInput{}, fmt.Errorf("decode provider input: %w", err)
	}
	if input.SchemaVersion != "1.0" || input.StandardID != fixtureStandard || input.Version != fixtureVersion {
		return wireRequest{}, providerInput{}, errors.New("provider input identity does not match fixture")
	}
	switch input.Operation {
	case "render", "validate", "verify", "drift-check":
	default:
		return wireRequest{}, providerInput{}, errors.New("provider input operation is unsupported")
	}
	return request, input, nil
}

func decodeStrict(reader io.Reader, target any) error {
	decoder := json.NewDecoder(reader)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(target); err != nil {
		return err
	}
	var trailing json.RawMessage
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		if err == nil {
			return errors.New("JSON request contains trailing data")
		}
		return err
	}
	return nil
}

func execute(request wireRequest, input providerInput) (providerResult, error) {
	if len(request.Resources) != 1 || len(input.Resources) != 1 {
		return providerResult{}, errors.New("command request must carry exactly one declared resource")
	}
	encodedResource, ok := request.Resources[resourceID]
	if !ok {
		return providerResult{}, errors.New("command request omitted the declared resource")
	}
	resource, err := base64.StdEncoding.Strict().DecodeString(encodedResource)
	if err != nil || base64.StdEncoding.EncodeToString(resource) != encodedResource {
		return providerResult{}, errors.New("command request resource is not canonical base64")
	}
	digest := sha256.Sum256(resource)
	digestText := "sha256:" + hex.EncodeToString(digest[:])
	if input.Resources[resourceID] != digestText {
		return providerResult{}, errors.New("command request resource digest does not match input")
	}

	observed := observedResult{
		SchemaVersion:  request.SchemaVersion,
		StandardID:     input.StandardID,
		Version:        input.Version,
		Operation:      input.Operation,
		ResourceBase64: encodedResource,
		ResourceDigest: digestText,
		Snapshots:      input.Snapshots,
		Environment:    os.Environ(),
	}
	if input.Operation == "render" {
		return providerResult{
			Content:  fmt.Sprintf("%s|%s|%s", input.StandardID, input.Operation, resource),
			Observed: observed,
		}, nil
	}
	return providerResult{
		Findings: []finding{{
			Code:     "FIXTURE-COMMAND-PROVIDER",
			Severity: "warning",
			Path:     ".standards/command-provider-fixture.txt",
			Identity: fixtureStandard + "/" + input.Operation,
			Message:  "synthetic command provider completed " + input.Operation,
			Hint:     "no action is required for the synthetic fixture",
		}},
		Observed: observed,
	}, nil
}
