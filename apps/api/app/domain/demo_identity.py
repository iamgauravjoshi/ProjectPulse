"""Durable demo identities: product renames must not duplicate existing records."""

from uuid import UUID

DEMO_IDS = {
    "project": UUID("b0b0fead-d9da-54f3-9fd2-aac6e7ab1a0d"),
    "sarah": UUID("892b7c18-5b23-526f-a899-757d871d7a06"),
    "john": UUID("96edfec9-964b-576c-a75d-3cd3ca896495"),
    "alex": UUID("5ea74d6b-63cf-5376-bfe8-49fad55ddd60"),
    "maya": UUID("acf0a681-26e8-5ec9-93d3-5a7f6276fd72"),
    "member-sarah": UUID("86e2a8e9-cc14-5106-8a1d-bafbcc2ffe31"),
    "member-john": UUID("b425237f-127c-5a46-9e7b-db0004a80c86"),
    "member-alex": UUID("5db9f04b-18ab-5f6f-8913-d425d261e4ad"),
    "member-maya": UUID("1be05201-123d-54ea-a5dd-0a5e9bb4e211"),
    "sso": UUID("d026eb9e-1330-5a0b-a5b1-c26305569fc7"),
    "launch": UUID("5ccb197b-e265-5b97-971a-17f82788c0ac"),
    "database": UUID("2dc82bc4-8043-524b-a0d8-337ed901c364"),
    "csv-export": UUID("39517df1-3b09-50f2-aa2a-23922752448f"),
    "payment-retries": UUID("80caf862-da5c-5a04-9eaa-5ca4cf715af7"),
    "security-review": UUID("540513e6-ba7c-5ec1-9825-39a459c1e0fb"),
    "credentials": UUID("6607c14e-add2-5dcb-afda-d4a3e8b97dde"),
    "security-risk": UUID("68f92932-c3eb-5681-9da0-96973cd4735f"),
    "security-question": UUID("5b896da5-90d9-553b-9880-c40aac7fec66"),
    "seed-audit": UUID("f70bc2fc-e53c-5592-b412-9e230840e3b8"),
}


def demo_id(label: str) -> UUID:
    return DEMO_IDS[label]
