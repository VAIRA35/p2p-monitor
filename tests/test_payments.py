from app.payments import normalize_payment


def test_bank_aliases():
    assert normalize_payment("Monobank (IBAN)") == "monobank"
    assert normalize_payment("PrivatBank (CARD)") == "privatbank"
    assert normalize_payment("Privat Bank") == "privatbank"
    assert normalize_payment("A-Bank (CARD)") == "a-bank"
    assert normalize_payment("Sense SuperApp") == "sense"
    assert normalize_payment("bank") == "bank transfer"
    assert normalize_payment("Bank Transfer") == "bank transfer"


def test_unknown_kept_lowercase():
    assert normalize_payment("Some New Bank") == "some new bank"
