use agenttrace_core::{Event, TraceReader, TraceWriter};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};
use pythonize::depythonize;
use std::path::PathBuf;

#[pyclass]
struct CoreTracer {
    writer: Option<TraceWriter>,
}

#[pymethods]
impl CoreTracer {
    #[new]
    fn new(trace_id: String, root: String) -> PyResult<Self> {
        let path = PathBuf::from(root);
        let writer = TraceWriter::start(&trace_id, &path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        Ok(CoreTracer {
            writer: Some(writer),
        })
    }

    fn emit(&mut self, trace_id: String, seq: u64, kind: String, payload_dict: &PyDict) -> PyResult<()> {
        if let Some(writer) = &mut self.writer {
            // Convert PyDict to serde_json::Value
            let payload: serde_json::Value = depythonize(payload_dict)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

            let event = Event::new(trace_id, seq, kind, payload);
            
            writer.emit(&event)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            return Ok(());
        }
        Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Tracer closed"))
    }

    fn finish(&mut self) -> PyResult<()> {
        if let Some(writer) = self.writer.take() {
            writer.finish()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        }
        Ok(())
    }
}

#[pyclass]
struct CoreReader {
    reader: TraceReader,
}

#[pymethods]
impl CoreReader {
    #[new]
    fn new(root: String) -> Self {
        CoreReader {
            reader: TraceReader::new(PathBuf::from(root)),
        }
    }

    fn list_traces(&self) -> PyResult<Vec<String>> {
        let meta = self.reader.list_traces()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        Ok(meta.into_iter().map(|m| m.id).collect())
    }

    fn get_events_json(&self, trace_id: String) -> PyResult<Vec<String>> {
        // We return raw JSON strings to avoid expensive pyobject conversion overhead for now
        let events = self.reader.get_events(&trace_id)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        let mut out = Vec::with_capacity(events.len());
        for ev in events {
            let s = serde_json::to_string(&ev)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            out.push(s);
        }
        Ok(out)
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn _core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<CoreTracer>()?;
    m.add_class::<CoreReader>()?;
    Ok(())
}
