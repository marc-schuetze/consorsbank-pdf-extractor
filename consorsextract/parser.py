"""
Transaction data extraction for Consorsbank Girokonto statements.

The statement body (rendered with ``pdftotext -layout``) looks like::

    Text/Verwendungszweck            Datum       PNNr     Wert          Soll        Haben
    EURO-UEBERW.                     09.01. 8420          09.01.        300,00-
        MARC SCHUETZE
       <GENODEF1S15>    DE74200905000001433822
       Gemeinschaftskonto Ausgleich
    *** Kontostand zum 09.01. ***                                                 7.606,74+

Each transaction is:
  * a *header line*: ``<type>  <booking date>  <PNNr>  <value date>  <amount><sign>``
  * a *name line* (recipient/sender)
  * a *party line*: ``<BIC>    <IBAN>``
  * zero or more *purpose lines* (Verwendungszweck)

Running balances appear as ``*** Kontostand zum DD.MM. *** <balance>`` and are
used only for reconciliation, not emitted as transactions.
"""
import logging
import re

# Header line: type, booking date, PNNr, value date, amount with trailing sign.
# `type` is non-greedy so multi-word types (GEHALT/RENTE, STORNO GEB) are kept whole.
TXN_RE = re.compile(
    r"^\s*(?P<type>\S.*?)\s+"
    r"(?P<bdate>\d{2}\.\d{2}\.)\s+"
    r"(?P<pnnr>\d{3,4})\s+"
    r"(?P<vdate>\d{2}\.\d{2}\.)\s+"
    r"(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2})(?P<sign>[+-])\s*$"
)

# Party line: <BIC>  IBAN   (BIC may be padded with spaces inside the brackets)
PARTY_RE = re.compile(r"<\s*(?P<bic>[A-Z0-9 ]+?)\s*>\s*(?P<iban>[A-Z]{2}[0-9A-Z ]+)?")

# Running balance checkpoint
CHECKPOINT_RE = re.compile(
    r"^\*\*\*\s*Kontostand zum\s+(?P<date>\d{2}\.\d{2}\.)\s*\*\*\*\s+"
    r"(?P<balance>\d{1,3}(?:\.\d{3})*,\d{2})(?P<sign>[+-])"
)

DATE_HEADER_RE = re.compile(r"^\s*Datum\s+(\d{2})\.(\d{2})\.(\d{2})\b")

# A bare signed amount on its own (used to read the balance under a label)
BARE_AMOUNT_RE = re.compile(r"^\s*(\d{1,3}(?:\.\d{3})*,\d{2})([+-])\s*$")

# Lines that never belong to a transaction's purpose text (page footer boilerplate etc.)
NOISE_PREFIXES = (
    "Consorsbank",
    "Standort N",
    "Fon +49",
    "Sitz der BNP",
    "Président",
    "Kontoauszug",
    "Kontoabschluss",
    "Datum ",
    "BIC ",
    "IBAN ",
    "Bankleitzahl",
    "Text/Verwendungszweck",
    "Hinweis f",
    "Einwendungen",
    "Machen Sie",
    "Guthaben sind",
    "\f",
)


def parse_amount(amount_str, sign):
    """Convert a German-formatted amount + trailing sign to a signed float.

    ``"3.806,44", "-"`` -> ``-3806.44``;  ``"321,30", "+"`` -> ``321.30``.
    """
    value = float(amount_str.replace(".", "").replace(",", "."))
    return -value if sign == "-" else value


def find_current_year_from_text(extracted_text):
    """Extract the full statement year from the ``Datum DD.MM.YY`` header.

    Returns a four-digit year string (e.g. ``"2017"``); defaults to ``None`` if
    no date header is found.
    """
    for line in extracted_text.split("\n"):
        m = DATE_HEADER_RE.match(line)
        if m:
            yy = m.group(3)
            return "20" + yy
    logging.debug("No statement date header found (not a transaction statement)")
    return None


def find_balance_after_label(text, label):
    """Read the signed amount printed on the line below ``label``.

    Consorsbank prints ``Buchungssaldo alt`` / ``Buchungssaldo neu`` as a
    right-aligned label with the value on the following line. Returns a float or
    None if the label/value is absent.
    """
    lines = text.split("\n")
    for idx, line in enumerate(lines):
        if label in line:
            for follow in lines[idx + 1:idx + 4]:
                m = BARE_AMOUNT_RE.match(follow)
                if m:
                    return parse_amount(m.group(1), m.group(2))
            return None
    return None


def _is_noise(line):
    stripped = line.strip()
    if not stripped:
        return True
    return any(stripped.startswith(p) or line.startswith(p) for p in NOISE_PREFIXES)


def parse_statement(text, year, source_file):
    """Parse all transactions and balance checkpoints from one statement.

    Args:
        text (str): ``pdftotext -layout`` output for a single statement.
        year (str): Four-digit year for the statement.
        source_file (str): Filename, recorded on each transaction.

    Returns:
        tuple(list[dict], list[dict]): (transactions, checkpoints)
        Each transaction dict has: booking_date, value_date, type, pnnr, name,
        bic, iban, amount (float), purpose, source_file. Each checkpoint has:
        date, balance (float). Both lists are in statement order, interleaved by
        the ``_order`` key so reconciliation can walk them together.
    """
    lines = text.split("\n")
    transactions = []
    checkpoints = []
    order = 0
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        cp = CHECKPOINT_RE.match(line.strip())
        if cp:
            checkpoints.append({
                "date": cp.group("date") + year,
                "balance": parse_amount(cp.group("balance"), cp.group("sign")),
                "_order": order,
            })
            order += 1
            i += 1
            continue

        m = TXN_RE.match(line)
        if not m:
            i += 1
            continue

        txn = {
            "booking_date": m.group("bdate") + year,
            "value_date": m.group("vdate") + year,
            "type": m.group("type").strip(),
            "pnnr": m.group("pnnr"),
            "amount": parse_amount(m.group("amount"), m.group("sign")),
            "name": "",
            "bic": "",
            "iban": "",
            "purpose": "",
            "source_file": source_file,
            "_order": order,
        }
        order += 1

        # Collect the detail lines that follow, until the next transaction,
        # the next checkpoint, or end of statement.
        name = None
        purpose_parts = []
        j = i + 1
        while j < n:
            nxt = lines[j]
            if TXN_RE.match(nxt) or CHECKPOINT_RE.match(nxt.strip()):
                break
            party = PARTY_RE.search(nxt)
            if party:
                txn["bic"] = re.sub(r"\s+", "", party.group("bic"))
                txn["iban"] = re.sub(r"\s+", "", party.group("iban") or "")
            elif not _is_noise(nxt):
                if name is None:
                    name = nxt.strip()
                else:
                    purpose_parts.append(nxt.strip())
            j += 1

        txn["name"] = name or ""
        txn["purpose"] = " ".join(purpose_parts)
        transactions.append(txn)
        i = j

    return transactions, checkpoints


def reconcile(transactions, checkpoints, opening_balance=None):
    """Check extracted amounts against the statement's running balances.

    Walks transactions and checkpoints in statement order. At each checkpoint the
    accumulated balance must equal the printed balance (within 0.5 cent).

    Args:
        transactions, checkpoints: outputs of :func:`parse_statement`.
        opening_balance (float|None): seed balance. If None, the running sum is
            anchored at the first checkpoint instead of verified against it.

    Returns:
        list[dict]: one entry per checkpoint with date, expected, actual, ok.
    """
    events = sorted(
        [("txn", t["_order"], t["amount"]) for t in transactions]
        + [("cp", c["_order"], c) for c in checkpoints],
        key=lambda e: e[1],
    )

    running = opening_balance
    results = []
    for kind, _order, payload in events:
        if kind == "txn":
            if running is not None:
                running += payload
        else:  # checkpoint
            printed = payload["balance"]
            if running is None:
                running = printed  # anchor on first checkpoint
                ok = True
            else:
                ok = abs(running - printed) < 0.005
            results.append({
                "date": payload["date"],
                "expected": printed,
                "actual": round(running, 2),
                "ok": ok,
            })
            running = printed  # resync so one bad txn flags only one checkpoint
    return results
