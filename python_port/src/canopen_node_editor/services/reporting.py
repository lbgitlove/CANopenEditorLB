"""HTML reporting for validation summaries."""
from __future__ import annotations

from collections import Counter
from typing import Iterable

from jinja2 import Environment, select_autoescape

from ..model import Device
from ..validation import ValidationIssue

_TEMPLATE = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>{{ device.info.product_name or "CANopen Device" }} – Validation Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; }
    h1 { font-size: 1.8rem; }
    table { border-collapse: collapse; width: 100%; margin-top: 1.5rem; }
    th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: left; }
    th { background: #f0f0f0; }
    .severity-error { color: #b00020; font-weight: bold; }
    .severity-warning { color: #b8860b; font-weight: bold; }
  </style>
</head>
<body>
  <h1>Validation Report – {{ device.info.product_name or "CANopen Device" }}</h1>
  <section>
    <h2>Summary</h2>
    <p>Total issues: {{ issues|length }}.</p>
    <ul>
    {% for severity, count in severity_counts.items() %}
      <li><span class=\"severity-{{ severity }}\">{{ severity.title() }}</span>: {{ count }}</li>
    {% endfor %}
    </ul>
  </section>
  <section>
    <h2>Device Information</h2>
    <ul>
      <li><strong>Vendor:</strong> {{ device.info.vendor_name or "Unknown" }}</li>
      <li><strong>Product:</strong> {{ device.info.product_name or "Unknown" }}</li>
      <li><strong>Revision:</strong> {{ device.info.revision_number or "Unknown" }}</li>
    </ul>
  </section>
  <section>
    <h2>Issues</h2>
    <table>
      <thead>
        <tr><th>Severity</th><th>Code</th><th>Message</th><th>Index</th><th>SubIndex</th></tr>
      </thead>
      <tbody>
      {% for issue in issues %}
        <tr>
          <td class=\"severity-{{ issue.severity }}\">{{ issue.severity.title() }}</td>
          <td>{{ issue.code }}</td>
          <td>{{ issue.message }}</td>
          <td>{{ "0x%04X" % issue.index if issue.index is not none else "" }}</td>
          <td>{{ issue.subindex if issue.subindex is not none else "" }}</td>
        </tr>
      {% endfor %}
      {% if not issues %}
        <tr><td colspan=\"5\">No validation issues detected.</td></tr>
      {% endif %}
      </tbody>
    </table>
  </section>
</body>
</html>
"""

_env = Environment(autoescape=select_autoescape(enabled_extensions=("html",)))
_template = _env.from_string(_TEMPLATE)


def render_validation_report(device: Device, issues: Iterable[ValidationIssue]) -> str:
    """Render an HTML validation report for ``device``."""

    issue_list = list(issues)
    severity_counts = Counter(issue.severity for issue in issue_list)
    context = {"device": device, "issues": issue_list, "severity_counts": severity_counts}
    return _template.render(context)
