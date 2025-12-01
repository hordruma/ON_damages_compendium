"""Quick debug script to see what Camelot extracts"""
import camelot

PDF_PATH = "2024damagescompendium.pdf"
page_spec = "21-25"

print("="*80)
print("STREAM MODE:")
print("="*80)
tables_stream = camelot.read_pdf(PDF_PATH, pages=page_spec, flavor="stream")
print(f"Found {len(tables_stream)} tables\n")

for i, table in enumerate(tables_stream):
    print(f"\n--- Stream Table {i+1} (Page {table.page}) ---")
    df = table.df
    print(f"Shape: {df.shape}")
    print("\nFirst 5 rows:")
    for idx in range(min(5, len(df))):
        print(f"Row {idx}: {df.iloc[idx].tolist()}")

print("\n" + "="*80)
print("LATTICE MODE:")
print("="*80)
tables_lattice = camelot.read_pdf(PDF_PATH, pages=page_spec, flavor="lattice")
print(f"Found {len(tables_lattice)} tables\n")

for i, table in enumerate(tables_lattice):
    print(f"\n--- Lattice Table {i+1} (Page {table.page}) ---")
    df = table.df
    print(f"Shape: {df.shape}")
    print("\nFirst 5 rows:")
    for idx in range(min(5, len(df))):
        row_vals = df.iloc[idx].tolist()
        print(f"Row {idx}: {[str(v)[:50] for v in row_vals]}")
