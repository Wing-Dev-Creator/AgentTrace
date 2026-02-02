use agenttrace_core::{Event, TraceWriter};
use pyo3::exceptions::{PyFileNotFoundError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde_json::Value;
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};

#[pyclass]
struct NativeTraceWriter {
    trace_id: String,
    writer: Option<TraceWriter>,
}

#[pymethods]
impl NativeTraceWriter {
    #[new]
    fn new(trace_id: String, root: String) -> PyResult<Self> {
        let writer = TraceWriter::start(&trace_id, Path::new(&root))
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        Ok(Self {
            trace_id,
            writer: Some(writer),
        })
    }

    #[allow(clippy::too_many_arguments)]
    fn emit(
        &mut self,
        trace_id: String,
        seq: u64,
        ts_unix_ns: u128,
        kind: String,
        span_id: Option<String>,
        parent_span_id: Option<String>,
        level: String,
        attrs_json: String,
        payload_json: String,
    ) -> PyResult<()> {
        if trace_id != self.trace_id {
            return Err(PyValueError::new_err("trace_id mismatch for writer"));
        }

        let attrs_value: Value = serde_json::from_str(&attrs_json)
            .map_err(|err| PyValueError::new_err(format!("attrs_json invalid: {err}")))?;
        let payload_value: Value = serde_json::from_str(&payload_json)
            .map_err(|err| PyValueError::new_err(format!("payload_json invalid: {err}")))?;

        let attrs_map: HashMap<String, Value> = match attrs_value {
            Value::Object(map) => map.into_iter().collect(),
            Value::Null => HashMap::new(),
            _ => {
                return Err(PyValueError::new_err(
                    "attrs_json must be an object or null",
                ))
            }
        };

        let event = Event {
            trace_id,
            seq,
            ts_unix_ns,
            kind,
            span_id,
            parent_span_id,
            level,
            attrs: attrs_map,
            payload: payload_value,
        };

        match self.writer.as_mut() {
            Some(writer) => writer
                .emit(&event)
                .map_err(|err| PyRuntimeError::new_err(err.to_string()))?,
            None => return Err(PyRuntimeError::new_err("writer already finished")),
        }
        Ok(())
    }

    fn finish(&mut self) -> PyResult<()> {
        if let Some(writer) = self.writer.take() {
            writer
                .finish()
                .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        }
        Ok(())
    }
}

#[pyclass]
struct NativeTraceReader {
    root: PathBuf,
}

#[pymethods]
impl NativeTraceReader {
    #[new]
    fn new(root: String) -> Self {
        Self {
            root: PathBuf::from(root),
        }
    }

    fn list_traces(&self, py: Python<'_>) -> PyResult<PyObject> {
        if !self.root.exists() {
            return Ok(PyList::empty(py).into());
        }

        let mut traces: Vec<TraceMeta> = Vec::new();
        for entry in fs::read_dir(&self.root)
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))?
        {
            let entry = entry.map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
            let path = entry.path();
            if !path.is_dir() {
                continue;
            }

            let trace_id = entry.file_name().to_string_lossy().to_string();
            let mut meta = TraceMeta::new(&trace_id, path.metadata().ok());

            let events_path = path.join("events.jsonl");
            if events_path.exists() {
                if let Ok(file) = File::open(&events_path) {
                    let mut reader = BufReader::new(file);
                    let mut first_line = String::new();
                    if reader.read_line(&mut first_line).is_ok() {
                        let first_line = strip_crc(first_line.trim_end_matches('\r'));
                        if !first_line.is_empty() {
                            meta.has_first_line = true;
                            if let Ok(value) = serde_json::from_str::<Value>(first_line) {
                                if let Some((name, project, ts)) = extract_trace_meta(&value) {
                                    meta.name = name;
                                    meta.project = project;
                                    if let Some(ts) = ts {
                                        meta.ts = ts;
                                    }
                                }
                            }
                        }
                    }
                    let count = reader
                        .lines()
                        .filter(|l| {
                        l.as_ref().map(|line| !line.trim().is_empty()).unwrap_or(false)
                    })
                        .count();
                    meta.event_count = count as u64 + if meta.has_first_line { 1 } else { 0 };
                }
            }

            traces.push(meta);
        }

        traces.sort_by(|a, b| b.ts.partial_cmp(&a.ts).unwrap_or(std::cmp::Ordering::Equal));

        let list = PyList::empty(py);
        for trace in traces {
            let dict = PyDict::new(py);
            dict.set_item("id", trace.id)?;
            dict.set_item("name", trace.name)?;
            dict.set_item("project", trace.project)?;
            dict.set_item("ts", trace.ts)?;
            dict.set_item("event_count", trace.event_count)?;
            list.append(dict)?;
        }
        Ok(list.into())
    }

    fn get_events(&self, py: Python<'_>, trace_id: String) -> PyResult<PyObject> {
        let path = self.root.join(&trace_id).join("events.jsonl");
        if !path.exists() {
            return Err(PyFileNotFoundError::new_err(format!(
                "trace not found: {trace_id}"
            )));
        }

        let file =
            File::open(&path).map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        let reader = BufReader::new(file);
        let list = PyList::empty(py);
        for line in reader.lines() {
            let line = line.map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
            let line = strip_crc(line.trim_end_matches('\r'));
            if line.trim().is_empty() {
                continue;
            }
            let value: Value = serde_json::from_str(line)
                .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
            list.append(json_to_py(py, &value))?;
        }
        Ok(list.into())
    }
}

#[pymodule]
fn agenttrace_native(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_class::<NativeTraceWriter>()?;
    m.add_class::<NativeTraceReader>()?;
    Ok(())
}

struct TraceMeta {
    id: String,
    name: String,
    project: Option<String>,
    ts: f64,
    event_count: u64,
    has_first_line: bool,
}

impl TraceMeta {
    fn new(id: &str, metadata: Option<fs::Metadata>) -> Self {
        let ts = metadata
            .and_then(|meta| meta.modified().ok())
            .and_then(|mtime| mtime.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);
        Self {
            id: id.to_string(),
            name: id.to_string(),
            project: None,
            ts,
            event_count: 0,
            has_first_line: false,
        }
    }
}

fn extract_trace_meta(value: &Value) -> Option<(String, Option<String>, Option<f64>)> {
    let kind = value.get("kind")?.as_str()?;
    if kind != "trace_start" {
        return None;
    }
    let payload = value.get("payload")?;
    let payload_obj = payload.as_object()?;
    let name = payload_obj
        .get("trace_name")
        .and_then(|v| v.as_str())
        .unwrap_or("Untitled")
        .to_string();
    let project = payload_obj
        .get("project")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let ts = value
        .get("ts_unix_ns")
        .and_then(|v| v.as_u64())
        .map(|ns| ns as f64 / 1e9);
    Some((name, project, ts))
}

fn strip_crc(line: &str) -> &str {
    if let Some(tab_pos) = line.rfind('\t') {
        if line.len().saturating_sub(tab_pos + 1) == 8 {
            return &line[..tab_pos];
        }
    }
    line
}

fn json_to_py(py: Python<'_>, value: &Value) -> PyObject {
    match value {
        Value::Null => py.None(),
        Value::Bool(b) => b.into_py(py),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                i.into_py(py)
            } else if let Some(u) = n.as_u64() {
                u.into_py(py)
            } else if let Some(f) = n.as_f64() {
                f.into_py(py)
            } else {
                py.None()
            }
        }
        Value::String(s) => s.into_py(py),
        Value::Array(arr) => {
            let list = PyList::empty(py);
            for item in arr {
                list.append(json_to_py(py, item)).ok();
            }
            list.into_py(py)
        }
        Value::Object(map) => {
            let dict = PyDict::new(py);
            for (k, v) in map {
                dict.set_item(k, json_to_py(py, v)).ok();
            }
            dict.into_py(py)
        }
    }
}
