# API Documentation

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs` (Swagger UI)

## Endpoints

### Health Check
```
GET /health
→ {"status": "ok", "service": "maillard-backoffice"}
```

### Upload Invoice
```
POST /api/v1/upload/
Content-Type: multipart/form-data
Body: file (PDF, PNG, JPEG, or TIFF)

→ {
    "invoice_id": "uuid",
    "filename": "invoice.pdf",
    "status": "processed",
    "message": "Extracted 1234 chars, 8 line items"
  }
```

### List Invoices
```
GET /api/v1/invoices/?status=processed&limit=50&offset=0

→ [{ id, vendor_id, invoice_number, invoice_date, total, currency, status, ... }]
```

### Get Invoice Detail
```
GET /api/v1/invoices/{invoice_id}

→ {
    ...invoice fields,
    line_items: [
      {
        description: "Butter unsalted",
        raw_quantity_text: "5/20",
        cases: 5,
        units_per_case: 20,
        raw_quantity: 100,
        raw_unit: "oz",
        normalized_quantity: 2834.95,
        normalized_unit: "g",
        unit_price: 3.45,
        total_price: 345.00,
        normalized_unit_price: 0.121709
      }
    ]
  }
```

### List Vendors
```
GET /api/v1/vendors/

→ [{ id, name, normalized_name, ... }]
```

### Create Vendor
```
POST /api/v1/vendors/
Body: { "name": "Sysco", "contact_email": "..." }

→ { id, name, normalized_name, created_at }
```
