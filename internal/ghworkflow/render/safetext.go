package render

import "github.com/L3DigitalNet/project-standards/internal/ghworkflow/safetext"

// SanitizeText is the rendering layer's name for safetext.SanitizeText.
//
// The encoder moved to a leaf package in 1.10 so ghapi, cli, and audit could reach it
// without importing render (which would close an import cycle through the command
// packages). This alias keeps the rendering call sites — source.go, where every work
// item's untrusted text enters the model — reading as they did, and keeps render's own
// test of the encoding pointed at the surface renderers actually call.
func SanitizeText(text string) string { return safetext.SanitizeText(text) }
