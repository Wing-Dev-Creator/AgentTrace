use agenttrace_core::{Event, TraceReader, TraceWriter};
use pyo3::exceptions::{PyFileNotFoundError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde_json::Value;
use std::collections::HashMap;
use std::path::Path;

// ---------------------------------------------------------------------------
// NativeTraceWriter
// ---------------------------------------------------------------------------

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

    #[pyo3(signature = (trace_id, seq, ts_unix_ns, kind, span_id, parent_span_id, level, attrs_json, payload_json))]
    fn emit(
        &mut self,
        trace_id: String,
        seq: u64,
        ts_unix_ns: u64,
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

        let attrs: HashMap<String, Value> = serde_json::from_str(&attrs_json)
            .map_err(|e| PyValueError::new_err(format!("attrs_json invalid: {e}")))?;

        let payload: Value = serde_json::from_str(&payload_json)
            .map_err(|e| PyValueError::new_err(format!("payload_json invalid: {e}")))?;

        let event = Event {
            trace_id,
            seq,
            ts_unix_ns,
            kind,
            span_id,
            parent_span_id,
            level,
            attrs,
            payload,
        };

        match self.writer.as_mut() {
            Some(writer) => writer
                .emit(&event)
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?,
            None => return Err(PyRuntimeError::new_err("writer already finished")),
        }
        Ok(())
    }

    fn finish(&mut self) -> PyResult<()> {
        if let Some(writer) = self.writer.take() {
            writer
                .finish()
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// NativeTraceReader
// ---------------------------------------------------------------------------

#[pyclass]
struct NativeTraceReader {
    reader: TraceReader,
}

#[pymethods]
impl NativeTraceReader {
    #[new]
    fn new(root: String) -> Self {
        Self {
            reader: TraceReader::new(root),
        }
    }

    fn list_traces(&self, py: Python<'_>) -> PyResult<PyObject> {
        let traces = self
            .reader
            .list_traces()
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        let list = PyList::empty_bound(py);
        for t in &traces {
            let dict = PyDict::new_bound(py);
            dict.set_item("id", &t.id)?;
            dict.set_item("name", &t.name)?;
            dict.set_item("project", &t.project)?;
            dict.set_item("ts", t.ts)?;
            dict.set_item("event_count", t.event_count)?;
            list.append(dict)?;
        }
        Ok(list.into())
    }

    fn get_events(&self, py: Python<'_>, trace_id: String) -> PyResult<PyObject> {
        let events = self.reader.get_events(&trace_id).map_err(|e| {
            // Map TraceNotFound to Python FileNotFoundError, others to RuntimeError
            let msg = e.to_string();
            if msg.starts_with("trace not found") {
                PyFileNotFoundError::new_err(msg)
            } else {
                PyRuntimeError::new_err(msg)
            }
        })?;

        let list = PyList::empty_bound(py);
        for value in &events {
            list.append(json_to_py(py, value))?;
        }
        Ok(list.into())
    }
}

// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

#[pymodule]
fn agenttrace_native(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_class::<NativeTraceWriter>()?;
    m.add_class::<NativeTraceReader>()?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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
            let list = PyList::empty_bound(py);
            for item in arr {
                list.append(json_to_py(py, item)).ok();
            }
            list.into()
        }
        Value::Object(map) => {
            let dict = PyDict::new_bound(py);
            for (k, v) in map {
                dict.set_item(k, json_to_py(py, v)).ok();
            }
            dict.into()
        }
    }
}
