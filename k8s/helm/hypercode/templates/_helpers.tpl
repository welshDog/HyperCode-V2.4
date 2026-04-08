{{/*
HyperCode Helm chart helpers
*/}}

{{/*
Expand the chart name
*/}}
{{- define "hypercode.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name
*/}}
{{- define "hypercode.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart label
*/}}
{{- define "hypercode.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "hypercode.labels" -}}
helm.sh/chart: {{ include "hypercode.chart" . }}
{{ include "hypercode.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "hypercode.selectorLabels" -}}
app.kubernetes.io/name: {{ include "hypercode.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "hypercode.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "hypercode.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Image reference for a given component
Usage: {{ include "hypercode.image" (dict "root" . "component" .Values.core) }}
*/}}
{{- define "hypercode.image" -}}
{{- $reg := .component.image.registry | default .root.Values.image.registry }}
{{- $repo := .component.image.repository | default .root.Values.image.repository }}
{{- $tag := .component.image.tag | default .root.Chart.AppVersion }}
{{- printf "%s/%s:%s" $reg $repo $tag }}
{{- end }}

{{/*
Database URL helper
*/}}
{{- define "hypercode.databaseUrl" -}}
{{- printf "postgresql://hypercode@%s-postgresql:5432/hypercode" .Release.Name }}
{{- end }}

{{/*
Redis URL helper
*/}}
{{- define "hypercode.redisUrl" -}}
{{- printf "redis://%s-redis-master:6379" .Release.Name }}
{{- end }}
