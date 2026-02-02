pub fn calculate(data: &[u8]) -> u32 {
    crc32c::crc32c(data)
}

pub fn format_hex(crc: u32) -> String {
    format!("{:08x}", crc)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_crc_calculation() {
        let data = b"{\"hello\":\"world\"}";
        let crc = calculate(data);
        assert_ne!(crc, 0);
        let hex = format_hex(crc);
        assert_eq!(hex.len(), 8);
    }
}
