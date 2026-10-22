from app.guard import amounts, check_prices

CTX = "Out-Patient Program 3 Weeks $18,995. In-Patient $30,000. LAK $2,600 USD. Ethanol ablation: $3,800 - $4,250 USD."


def test_amount_normalisation():
    assert amounts("$18,995 and 18995 USD and US$18995") == {18995.0}
    assert amounts("about $18k") == {18000.0}
    assert amounts("3 weeks, 5 reviews") == set()


def test_valid_answer_passes():
    assert check_prices("The out-patient program is $18,995 (3 weeks); in-patient $30,000.", CTX) == []
    assert check_prices("Ethanol ablation costs $3,800 - $4,250 USD.", CTX) == []


def test_invented_or_calculated_price_is_caught():
    assert check_prices("It costs $50.", CTX)
    assert check_prices("Together that's $21,595.", CTX)               # no arithmetic allowed


def test_user_trick_price_cannot_be_confirmed():
    assert check_prices("Yes, $50 is right.", CTX, {50.0}, "supported")
    # correcting the user is fine: restating their number while contradicting it is allowed
    assert check_prices("No - the page lists $18,995, not $50.", CTX, {50.0}, "contradicted") == []
    assert check_prices("No - the page lists $18,995, not $50.", CTX, {50.0}, "not_found") == []
