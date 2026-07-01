{{/*
Expand the name of the chart.
*/}}
{{- define "ai101.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ai101.fullname" -}}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "ai101.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "ai101.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Image reference helper — avoids repeating registry/tag boilerplate.
Usage: {{ include "ai101.image" (dict "root" . "name" "agent") }}
*/}}
{{- define "ai101.image" -}}
{{- printf "%s/%s:%s" .root.Values.image.registry .name .root.Values.image.tag }}
{{- end }}
