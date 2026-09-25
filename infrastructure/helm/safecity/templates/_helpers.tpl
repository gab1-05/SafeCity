{{/* ─────────────────────────────────────────────────────────────
     SafeCity chart helpers
     ───────────────────────────────────────────────────────────── */}}

{{- define "safecity.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "safecity.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "safecity.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Common labels applied to every resource. */}}
{{- define "safecity.labels" -}}
helm.sh/chart: {{ include "safecity.chart" . }}
{{ include "safecity.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: safecity
environment: {{ .Values.global.environment | quote }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{/* Selector labels. MUST stay stable — changing these is a breaking change
     because selectors are immutable on StatefulSets and hard to change on
     Deployments. */}}
{{- define "safecity.selectorLabels" -}}
app.kubernetes.io/name: {{ include "safecity.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* Per-component labels: component must be "backend", "frontend",
     "celery-worker" or "celery-beat". */}}
{{- define "safecity.componentLabels" -}}
{{ include "safecity.labels" .root }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "safecity.componentSelectorLabels" -}}
{{ include "safecity.selectorLabels" .root }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* ── Service account ────────────────────────────────────── */}}
{{- define "safecity.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "safecity.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/* ── Secret name ────────────────────────────────────────── */}}
{{- define "safecity.secretName" -}}
{{- if .Values.secret.existingSecret -}}
{{- .Values.secret.existingSecret -}}
{{- else -}}
{{- printf "%s-secrets" (include "safecity.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/* ── Image reference ────────────────────────────────────── */}}
{{- define "safecity.image" -}}
{{- $registry := .root.Values.global.imageRegistry -}}
{{- $repository := .image.repository -}}
{{- $tag := .image.tag | default .root.Chart.AppVersion -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $repository $tag -}}
{{- else -}}
{{- printf "%s:%s" $repository $tag -}}
{{- end -}}
{{- end -}}

{{/* ── Effective endpoints ─────────────────────────────────────────────
     This chart does NOT deploy PostgreSQL or Redis. They are expected to be
     managed services (RDS + ElastiCache) or a separately-installed chart.
     The helpers below therefore fail loudly rather than silently resolving to
     a Service name that no template creates — a missing DB host produces a
     clear error instead of a CrashLoopBackOff and a confusing investigation.
     ─────────────────────────────────────────────────────────────────── */}}
{{- define "safecity.dbHost" -}}
{{- required "config.dbHost is required: set it to your PostgreSQL endpoint (RDS endpoint or a Service you manage separately)" .Values.config.dbHost -}}
{{- end -}}

{{- define "safecity.redisUrl" -}}
{{- required "config.redisUrl is required: set it to your Redis URL (e.g. redis://my-redis:6379/0)" .Values.config.redisUrl -}}
{{- end -}}

{{/* Celery uses a different logical database on the same Redis instance by
     default (db 1 vs db 0 for the cache/Channels layer). Override
     config.celeryBrokerUrl to point somewhere else entirely. */}}
{{- define "safecity.celeryBrokerUrl" -}}
{{- if .Values.config.celeryBrokerUrl -}}
{{- .Values.config.celeryBrokerUrl -}}
{{- else -}}
{{- include "safecity.redisUrl" . | regexReplaceAll "/[0-9]+$" "/1" -}}
{{- end -}}
{{- end -}}

{{/* ── Shared secret environment (from the Secret object) ─────────────
     Non-secret configuration is injected via the ConfigMap using envFrom,
     so it has exactly one definition (templates/configmap.yaml) rather than
     being duplicated per workload here.
     ─────────────────────────────────────────────────────────────────── */}}
{{- define "safecity.secretEnv" -}}
- name: SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "safecity.secretName" . }}
      key: secret-key
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "safecity.secretName" . }}
      key: postgres-password
- name: EMAIL_HOST_USER
  valueFrom:
    secretKeyRef:
      name: {{ include "safecity.secretName" . }}
      key: email-host-user
      optional: true
- name: EMAIL_HOST_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "safecity.secretName" . }}
      key: email-host-password
      optional: true
- name: OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "safecity.secretName" . }}
      key: openai-api-key
      optional: true
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: {{ include "safecity.secretName" . }}
      key: aws-access-key-id
      optional: true
- name: AWS_SECRET_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "safecity.secretName" . }}
      key: aws-secret-access-key
      optional: true
{{- end -}}

{{/* ── Writable emptyDir for /tmp (required by readOnlyRootFilesystem) ── */}}
{{- define "safecity.tmpVolume" -}}
- name: tmp
  emptyDir: {}
{{- end -}}

{{- define "safecity.tmpVolumeMount" -}}
- name: tmp
  mountPath: /tmp
{{- end -}}
