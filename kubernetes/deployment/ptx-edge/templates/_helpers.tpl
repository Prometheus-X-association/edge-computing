{{/*
Expand the name of the chart in a k8s conformant way.

Parameter: root context
*/}}
{{- define "edge.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create chart name and version as used by the chart label 'helm.sh/chart'.

Parameter: root context
*/}}
{{- define "edge.chart" -}}
{{- printf "%s-%s" (include "edge.name" .) .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Generate common labels for ptx-edge component manifests.

Parameters:
    0: root context
    1: name of the component b
    2: component tier (default: edge)
*/}}
{{- define "edge.commonLabels" -}}
{{- $root := index . 0 -}}
{{- $nameRef := index . 1 -}}
{{- $tier := "" -}}
{{- if gt (len .) 2 -}}
    {{- $tier = index . 2 -}}
{{- else -}}
  {{- $tier = "edge" -}}
{{- end -}}
app.kubernetes.io/name: {{ index $root.Values $nameRef "name" }}
{{- if $root.Chart.AppVersion }}
app.kubernetes.io/version: {{ $root.Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ $root.Release.Service }}
app.kubernetes.io/instance: {{ $root.Release.Name }}
helm.sh/chart: {{ include "edge.chart" $root }}
edge.dataspace.ptx.org/env: {{ default "development" $root.Values.global.env }}
edge.dataspace.ptx.org/tier: {{ default "edge" $tier }}
{{- end }}

{{/*
Add node selector to component which restricts deployment on nodes with control plate role.

Parameter: root context
*/}}
{{- define "edge.controlPlaneSelector" -}}
{{- if eq .Values.global.useControlPlane true -}}
nodeSelector:
  node-role.kubernetes.io/control-plane: "true"
{{- end -}}
{{- end -}}

{{/*
Reference of ptx-edge component's image based on configured registry url, port and the app version
Parameters:
    0: root context
    1: name of the component for extacting the image name
*/}}
{{- define "edge.imageRef" -}}
{{- $root := index . 0 -}}
{{- $imageKey := index . 1 -}}

{{- $registryUrl := $root.Values.registry.url -}}
{{- $registryPort := $root.Values.registry.port | toString -}}
{{- $imageName := required (printf "%s <image> is missing!" $imageKey) (index $root.Values $imageKey "image") -}}
{{- $version := $root.Chart.AppVersion | toString -}}

{{- if $registryUrl -}}
  {{- if and $registryPort (ne $registryPort "<nil>") (ne $registryPort "") -}}
    {{- printf "%s:%s/%s:%s" $registryUrl $registryPort $imageName $version -}}
  {{- else -}}
    {{- printf "%s/%s:%s" $registryUrl $imageName $version -}}
  {{- end -}}
{{- else -}}
  {{- printf "%s:%s" $imageName $version -}}
{{- end -}}
{{- end -}}

{{/*
Join path without duplicated slashes

Parameter: list of strings
*/}}
{{- define "edge.joinPath" -}}
{{- $parts := list -}}
{{- range . -}}
  {{- if . -}}
    {{- $cleaned := toString . | trimAll "/" -}}
    {{- if $cleaned -}}
      {{- $parts = append $parts $cleaned -}}
    {{- end -}}
  {{- end -}}
{{- end -}}
{{- printf "/%s" (join "/" $parts) -}}
{{- end -}}

{{/*
Assemble the mongoDB URI for the connector.

Parameter: root context
*/}}
{{- define "pdc.mongoURI" -}}
{{- $mongoUser := default "pdc" .Values.connector.credential.dbUser -}}
{{- $mongoPasswd := default (randAlphaNum 12) .Values.connector.credential.dbUser -}}
{{- $mongoURI := "mongodb://%s:%s@127.0.0.1:27017/dataspace-connector?authSource=dataspace-connector&appName=%s" -}}
{{- printf $mongoURI $mongoUser $mongoPasswd .Values.connector.name -}}
{{- end -}}

{{/*
Assemble the entrypoint URL template for the connector.

Parameter: root context
*/}}
{{- define "pdc.pdcEntrypoint" -}}
{{- $proto := default "http" .Values.gateway.proto -}}
{{- $gwHost := required "Gateway <host> is missing!" .Values.gateway.host -}}
{{- $gwPort := required "Gateway <port> is missing!" .Values.gateway.port | toString -}}
{{- printf "%s://%s:%s/%s/${PDC_DEF_PZ}/pdc" $proto $gwHost $gwPort .Release.Namespace  -}}
{{- end -}}