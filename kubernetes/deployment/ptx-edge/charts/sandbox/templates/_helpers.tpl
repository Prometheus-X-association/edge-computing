{{/*
Expand the name of the chart in a k8s conformant way.

Parameter: root context
*/}}
{{- define "sandbox.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label 'helm.sh/chart'.

Parameter: root context
*/}}
{{- define "sandbox.chart" -}}
{{- printf "%s-%s" (include "edge.name" .) .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Generate common labels for ptx-edge's sandbox component manifests.

Parameters:
    0: root context
    1: name of the component b
*/}}
{{- define "sandbox.commonLabels" -}}
{{- $root := index . 0 -}}
{{- $nameRef := index . 1 -}}

app.kubernetes.io/name: {{ index $root.Values $nameRef "name" | trunc 63 | trimSuffix "-" }}
{{- if $root.Chart.AppVersion }}
app.kubernetes.io/version: {{ $root.Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ $root.Release.Service }}
app.kubernetes.io/instance: {{ printf "%s-%s" $root.Release.Name $root.Chart.Name | trunc 63 | trimSuffix "-" }}
helm.sh/chart: {{ include "sandbox.chart" $root }}
edge.dataspace.ptx.org/env: sandbox
edge.dataspace.ptx.org/tier: testing
{{- end -}}