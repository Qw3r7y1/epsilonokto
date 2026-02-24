# Data Model

## Tables

### vendors
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(255) | Display name |
| normalized_name | VARCHAR(255) | Lowercased, stripped for matching |
| contact_email | VARCHAR(255) | Optional |
| phone | VARCHAR(50) | Optional |
| address | TEXT | Optional |
| notes | TEXT | Internal notes |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

### invoices
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| vendor_id | UUID → vendors | FK (nullable until matched) |
| original_filename | VARCHAR(500) | Upload filename |
| stored_path | VARCHAR(1000) | Disk/S3 path |
| file_hash | VARCHAR(64) | SHA-256 for dedup |
| file_type | VARCHAR(20) | pdf, png, jpg, etc. |
| invoice_number | VARCHAR(100) | Extracted |
| invoice_date | DATE | Extracted |
| due_date | DATE | Extracted |
| subtotal | NUMERIC(12,2) | Extracted |
| tax | NUMERIC(12,2) | Extracted |
| total | NUMERIC(12,2) | Extracted |
| currency | VARCHAR(3) | Default USD |
| raw_text | TEXT | Full OCR/PDF text |
| status | VARCHAR(20) | pending/processed/failed/review |
| extraction_confidence | NUMERIC(5,2) | 0–100 |

### products
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(255) | Product name |
| normalized_name | VARCHAR(255) | For matching |
| category | VARCHAR(100) | e.g. Dairy, Produce |
| compare_mode | VARCHAR(20) | weight/volume/count/none |
| base_unit | VARCHAR(20) | Display unit (kg, oz, L, ea) |

### line_items
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| invoice_id | UUID → invoices | FK |
| product_id | UUID → products | FK (nullable) |
| description | TEXT | Raw line text |
| raw_quantity_text | VARCHAR(50) | Original text: "5/20", "10" |
| cases | NUMERIC(10,3) | Cases count (null if simple) |
| units_per_case | NUMERIC(10,3) | Units per case (null if simple) |
| raw_quantity | NUMERIC(12,3) | Total = cases × units_per_case |
| raw_unit | VARCHAR(50) | Unit as written: oz, lb, gal |
| normalized_quantity | NUMERIC(14,4) | In base unit (g, ml, ea) |
| normalized_unit | VARCHAR(20) | g, ml, or ea |
| unit_price | NUMERIC(12,4) | Price per raw unit |
| total_price | NUMERIC(12,2) | Line total |
| normalized_unit_price | NUMERIC(14,6) | Price per base unit |
| position | INTEGER | Row order on invoice |

## Quantity Examples

| Invoice text | cases | units_per_case | raw_quantity | raw_unit | normalized_qty | norm_unit |
|---|---|---|---|---|---|---|
| 5/20 oz | 5 | 20 | 100 | oz | 2834.95 | g |
| 2/12 gal | 2 | 12 | 24 | gal | 90849.84 | ml |
| 10 lb | — | — | 10 | lb | 4535.92 | g |
| 3 cases | — | — | 3 | cases | 3 | ea |

## Relationships

```
Vendor 1──* Invoice 1──* LineItem *──1 Product
```
