use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Event {
    #[serde(default = "default_schema_version")]
    pub schema_version: u32,
    pub trace_id: String,
    pub seq: u64,
    pub ts_unix_ns: u64,
    pub kind: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub span_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent_span_id: Option<String>,
    pub level: String,
    pub attrs: HashMap<String, Value>,
    pub payload: Value,
}

impl Event {
    /// Convenience constructor for tests. Sets ts_unix_ns to current time,
    /// level to "info", and leaves span fields as None.
    pub fn new(trace_id: String, seq: u64, kind: String, payload: Value) -> Self {
        use std::time::{SystemTime, UNIX_EPOCH};
        let ts = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        Self {
            schema_version: default_schema_version(),
            trace_id,
            seq,
            ts_unix_ns: ts,
            kind,
            span_id: None,
            parent_span_id: None,
            level: "info".to_string(),
            attrs: HashMap::new(),
            payload,
        }
    }
}

fn default_schema_version() -> u32 {
    1
}
