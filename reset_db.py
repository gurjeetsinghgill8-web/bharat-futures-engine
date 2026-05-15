import db
db.load_secrets()

# Reset ALL symbol positions to FLAT
symbols = db.get_all_symbols()
for s in symbols:
    sym = s["symbol"]
    db.update_symbol_position(sym, "NONE", 0.0, 0, 0, 0)
    db.set_param("candle_ts_" + sym.upper(), "0")
    print("RESET: " + sym)

# Reset BTC candle guard too
db.set_param("candle_ts_BTCUSD", "0")
print("RESET: BTCUSD candle guard")

# Clean old trade locks
db.release_old_trade_locks(max_age_seconds=0)   # delete ALL locks
print("RESET: All trade locks cleared")

print("\nDB CLEAN. Bot will start fresh on restart.")
