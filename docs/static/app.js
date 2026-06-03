"use strict";

/* ---------- Data access shim ----------
   Single source of truth for both runtime modes:
     * Flask (local app, run.bat): window.CatalogEngine is undefined → use
       fetch() against the Python server's /api routes.
     * Static (GitHub Pages): catalog-engine.js defines window.CatalogEngine
       before this file loads → call its in-browser methods.
   This abstraction is the reason tools/build_static.py can copy app.js
   straight into docs/ without per-platform editing. */
const dataAPI = {
  async options(type, picks) {
    if (window.CatalogEngine) return window.CatalogEngine.options(type, picks);
    const url = `/api/${type}/options?picks=` + encodeURIComponent(JSON.stringify(picks));
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`options ${type}: HTTP ${resp.status}`);
    return resp.json();
  },
  async resolve(type, picks) {
    if (window.CatalogEngine) return window.CatalogEngine.resolve(type, picks);
    const url = `/api/${type}/resolve?picks=` + encodeURIComponent(JSON.stringify(picks));
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`resolve ${type}: HTTP ${resp.status}`);
    return resp.json();
  },
  async accessories() {
    if (window.CatalogEngine) return window.CatalogEngine.accessories();
    const resp = await fetch("/api/accessories/list");
    if (!resp.ok) throw new Error(`accessories: HTTP ${resp.status}`);
    return resp.json();
  },
};

class Picker {
  // valveType -> Picker, populated by the constructor. Lets the "View matching
  // actuator" button on one section drive the picker in another section.
  static instances = new Map();

  constructor(sectionEl) {
    this.section = sectionEl;
    this.valveType = sectionEl.dataset.valveType;
    this.form = sectionEl.querySelector(".picker");
    this.fields = Array.from(this.form.querySelectorAll("select, input[list]"));
    this.fieldKeys = this.fields.map((f) => f.dataset.key);

    this.validOptions = new Map();

    this.statusEl = sectionEl.querySelector(".status");
    this.codesEl = sectionEl.querySelector(".codes");
    this.primaryEl = sectionEl.querySelector(".primary-code");
    this.secondaryEl = sectionEl.querySelector(".secondary-code");
    this.btoEl = sectionEl.querySelector(".bto");
    this.fosEl = sectionEl.querySelector(".fos");
    this.altNote = sectionEl.querySelector(".alt-note");
    this.pairedActuatorEl = sectionEl.querySelector(".paired-actuator");
    this.detailsWrap = sectionEl.querySelector(".details-wrap");
    this.detailsTable = sectionEl.querySelector(".details tbody");
    this.resetBtn = sectionEl.querySelector(".reset-btn");

    Picker.instances.set(this.valveType, this);
    this._wire();
    this.init();
  }

  _wire() {
    for (const f of this.fields) {
      f.addEventListener("change", (ev) => this._onChange(ev));
      if (this._isTypeahead(f)) {
        f.addEventListener("input", () => {
          const valid = this.validOptions.get(f.dataset.key) || [];
          if (valid.includes(f.value)) this._onChange({ target: f });
        });
      }
    }
    this.resetBtn.addEventListener("click", async () => {
      for (const f of this.fields) f.value = "";
      await this.refreshOptions();
      await this.refreshResolution();
    });
  }

  _isTypeahead(field) { return field.tagName === "INPUT"; }

  _currentPicks() {
    const picks = {};
    for (const f of this.fields) {
      const val = f.value;
      if (!val) continue;
      if (this._isTypeahead(f)) {
        const valid = this.validOptions.get(f.dataset.key) || [];
        if (!valid.includes(val)) continue;
      }
      picks[f.dataset.key] = val;
    }
    return picks;
  }

  _fillField(field, options, prevValue) {
    this.validOptions.set(field.dataset.key, options);

    if (this._isTypeahead(field)) {
      const datalist = document.getElementById(field.getAttribute("list"));
      datalist.innerHTML = "";
      for (const v of options) {
        const opt = document.createElement("option");
        opt.value = v;
        datalist.appendChild(opt);
      }
      if (field.value && !options.includes(field.value)) field.value = "";
      if (prevValue && options.includes(prevValue) && !field.value) field.value = prevValue;
      if (options.length === 1 && !field.value) field.value = options[0];
      return;
    }

    field.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = options.length ? "— select —" : "(not applicable)";
    field.appendChild(placeholder);
    for (const v of options) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      field.appendChild(opt);
    }
    if (prevValue && options.includes(prevValue)) field.value = prevValue;
    if (options.length === 1 && !field.value) field.value = options[0];
  }

  async refreshOptions() {
    const picks = this._currentPicks();
    let opts;
    try {
      opts = await dataAPI.options(this.valveType, picks);
    } catch (e) {
      this.statusEl.textContent = "Server error loading options.";
      return;
    }
    for (const f of this.fields) {
      const k = f.dataset.key;
      if (k in picks) continue;
      this._fillField(f, opts[k] || [], f.value);
    }
  }

  async refreshResolution() {
    const picks = this._currentPicks();
    // A field with zero available options is N/A for the current selection
    // (e.g. "No. of Springs" on a Double Acting actuator). Treat it as
    // implicitly satisfied so the resolution can complete.
    const requiredKeys = this.fieldKeys.filter((k) => {
      if (k in picks) return true;
      const opts = this.validOptions.get(k) || [];
      return opts.length > 0;
    });
    const filled = Object.keys(picks).length;
    if (filled < requiredKeys.length) {
      const firstLabel = this.fields[0]?.previousElementSibling?.textContent?.trim() || "first field";
      this.statusEl.textContent = filled === 0
        ? `Pick ${firstLabel} to begin.`
        : `Continue selecting (${filled}/${requiredKeys.length}).`;
      this.codesEl.hidden = true;
      this.altNote.hidden = true;
      this._renderPairedActuators(null);
      this.detailsWrap.hidden = true;
      this._emitClearedEvent();
      return;
    }
    const data = await dataAPI.resolve(this.valveType, picks);
    if (!data.matched) {
      this.statusEl.textContent = "No SKU matches this combination.";
      this.codesEl.hidden = true;
      this.altNote.hidden = true;
      this._renderPairedActuators(null);
      this.detailsWrap.hidden = true;
      this._emitClearedEvent();
      return;
    }
    const d = data.detail;
    this.statusEl.textContent = "Here's your match!";
    if (this.primaryEl)   this.primaryEl.textContent = d.primary ?? "—";
    if (this.secondaryEl) this.secondaryEl.textContent = d.secondary ?? "—";
    if (this.btoEl)       this.btoEl.textContent = d.bto ?? "—";
    if (this.fosEl)       this.fosEl.textContent = d.fos ?? "—";
    this.codesEl.hidden = false;
    this._emitResolvedEvent(d);

    if (d.match_count > 1) {
      this.altNote.hidden = false;
      this.altNote.textContent = `${d.match_count} catalog rows matched these picks — showing the first.`;
    } else {
      this.altNote.hidden = true;
    }

    this._renderPairedActuators(d.paired_actuators || null);

    this.detailsTable.innerHTML = "";
    for (const f of d.fields) {
      const tr = document.createElement("tr");
      const th = document.createElement("th");
      th.textContent = f.label;
      const td = document.createElement("td");
      td.textContent = f.value == null || f.value === "" ? "—" : f.value;
      tr.appendChild(th);
      tr.appendChild(td);
      this.detailsTable.appendChild(tr);
    }
    this.detailsWrap.hidden = false;
  }

  _renderPairedActuators(list) {
    if (!this.pairedActuatorEl) return;
    this.pairedActuatorEl.replaceChildren();
    if (!list || list.length === 0) {
      this.pairedActuatorEl.hidden = true;
      return;
    }

    // Group by category — pneumatic_* → "Pneumatic", electrical_* → "Electric".
    // Preserves the order the entries appear in (so Pneumatic Option 1 comes
    // before Electric Option 2 when both exist).
    const groups = new Map();
    for (const paired of list) {
      const category = paired.target_type === "electrical_rotary"
        ? "Electric"
        : "Pneumatic";
      if (!groups.has(category)) groups.set(category, []);
      groups.get(category).push(paired);
    }

    // Single top-level section heading. The user explicitly asked for ONE
    // "Recommended Actuator" header — multiple per-card headers felt shabby
    // when several options share the same category.
    const section = document.createElement("section");
    section.className = "paired-section";

    const header = document.createElement("h3");
    header.className = "paired-section-header";
    header.textContent = "Recommended Actuator";
    section.appendChild(header);

    let optionNum = 1;
    for (const [category, items] of groups) {
      const group = document.createElement("div");
      group.className = "paired-option-group";

      const label = document.createElement("div");
      label.className = "paired-option-label";
      const optionEl = document.createElement("span");
      optionEl.className = "paired-option-num";
      optionEl.textContent = `Option ${optionNum}`;
      const catEl = document.createElement("span");
      catEl.className = "paired-option-cat";
      catEl.textContent = category;
      label.appendChild(optionEl);
      label.appendChild(catEl);
      group.appendChild(label);

      const chipsRow = document.createElement("div");
      chipsRow.className = "paired-chips";

      for (const paired of items) {
        chipsRow.appendChild(this._renderPairedChip(paired));
      }

      group.appendChild(chipsRow);
      section.appendChild(group);
      optionNum++;
    }

    this.pairedActuatorEl.appendChild(section);
    this.pairedActuatorEl.hidden = false;
  }

  /* One small selectable chip for a single recommended model.
     Two-line layout: model code on top (primary, monospace), position
     label below (smaller, descriptive). The label is the source-file
     column header (e.g. "Double Acting @ 3.5 bar"), stripped of the
     redundant category prefix since the group heading already shows it. */
  _renderPairedChip(paired) {
    const isUnavailable = paired.not_in_catalog === true;

    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "paired-chip";

    const codeEl = document.createElement("span");
    codeEl.className = "paired-chip-code";
    codeEl.textContent = paired.model;
    chip.appendChild(codeEl);

    // paired.label is e.g. "Pneumatic — Double Acting @ 3.5 bar".
    // Strip the category prefix since the group heading already shows it.
    const positionLabel = (paired.label || "").replace(
      /^(Pneumatic|Electric)\s*—\s*/, ""
    );
    if (positionLabel) {
      const labelEl = document.createElement("span");
      labelEl.className = "paired-chip-label";
      labelEl.textContent = positionLabel;
      chip.appendChild(labelEl);
    }

    // Tooltip: friendly actuator name (from destination catalog lookup) or
    // unavailable note. The position label is already visible, no need to
    // repeat it.
    if (isUnavailable) {
      chip.title = "Data Not Available — catalog entry pending";
    } else if (paired.name) {
      chip.title = paired.name;
    }

    if (isUnavailable) {
      chip.classList.add("paired-chip--unavailable");
      chip.disabled = true;
    } else {
      chip.addEventListener("click", () => {
        viewMatchingActuator(paired.target_type, paired.target_field, paired.model);
      });
    }
    return chip;
  }

  /** Programmatically set a field to `value`, then refresh options + result.
   *  Used by the cross-section "View matching actuator" button. */
  async setFieldValue(key, value) {
    const field = this.fields.find((f) => f.dataset.key === key);
    if (!field) return;
    field.value = value;
    // Mimic the downstream-reset behavior of _onChange.
    const changedIdx = this.fieldKeys.indexOf(key);
    for (let i = changedIdx + 1; i < this.fields.length; i++) {
      this.fields[i].value = "";
    }
    await this.refreshOptions();
    await this.refreshResolution();
  }

  async _onChange(ev) {
    const changedIdx = this.fieldKeys.indexOf(ev.target.dataset.key);
    for (let i = changedIdx + 1; i < this.fields.length; i++) {
      this.fields[i].value = "";
    }
    await this.refreshOptions();
    await this.refreshResolution();
  }

  async init() {
    await this.refreshOptions();
    await this.refreshResolution();
  }

  /* Notify the SummaryPanel (and anything else listening) that this section
     has produced a resolved Code. Custom event bubbles to document so the
     SummaryPanel can attach one listener at the top level. */
  _emitResolvedEvent(d) {
    const titleEl = this.section.querySelector(".section-title");
    // Strip any leading subgroup chip text (e.g. "Pneumatic Rack & Pinion"
    // -> "Rack & Pinion") so the summary shows just the family label.
    const subgroupEl = this.section.querySelector(".section-subgroup");
    let sectionLabel = titleEl ? titleEl.textContent.trim() : this.valveType;
    if (subgroupEl) {
      sectionLabel = sectionLabel.replace(subgroupEl.textContent.trim(), "").trim();
    }
    // For actuators, pull the descriptive "Actuator" detail field (e.g.
    // "Pneumatic Rack & Pinion Actuator") if present.
    const actuatorField = (d.fields || []).find((f) => f.label === "Actuator");
    const typeField     = (d.fields || []).find((f) => f.label === "Type");

    this.section.dispatchEvent(new CustomEvent("valve-selector:resolved", {
      bubbles: true,
      detail: {
        key: this.valveType,
        category: this.section.dataset.category,
        sectionLabel: sectionLabel,
        primary: d.primary,
        secondary: d.secondary,
        actuatorName: actuatorField ? actuatorField.value : null,
        actuatorType: typeField ? typeField.value : null,
      },
    }));
  }

  _emitClearedEvent() {
    this.section.dispatchEvent(new CustomEvent("valve-selector:cleared", {
      bubbles: true,
      detail: {
        key: this.valveType,
        category: this.section.dataset.category,
      },
    }));
  }
}

document.querySelectorAll(".valve-section").forEach((s) => new Picker(s));

/* ---------- Per-category type pickers ----------
   Each .type-picker has its own popover. Selections are MUTUALLY EXCLUSIVE
   across pickers: picking a type in one closes whatever section is open in
   the other. Clicking the already-active option deselects it (back to empty
   state). */
class TypePicker {
  static instances = [];

  constructor(rootEl) {
    this.root = rootEl;
    this.category = rootEl.dataset.category;
    this.trigger = rootEl.querySelector(".type-picker-trigger");
    this.menu = rootEl.querySelector(".type-picker-menu");
    this.labelEl = rootEl.querySelector(".type-picker-trigger-label");
    this.initialLabel = this.labelEl.textContent;
    this.options = Array.from(rootEl.querySelectorAll(".type-picker-option"));
    this.sections = Array.from(
      document.querySelectorAll(`.valve-section[data-category="${this.category}"]`)
    );
    this._onOutside = this._onOutside.bind(this);
    this._onKey = this._onKey.bind(this);
    this._wire();
    TypePicker.instances.push(this);
  }

  _wire() {
    this.trigger.addEventListener("click", () => this.toggle());
    for (const opt of this.options) {
      opt.addEventListener("click", () => this.select(opt.dataset.valveType));
    }
  }

  open() {
    this.menu.hidden = false;
    this.trigger.setAttribute("aria-expanded", "true");
    this.root.classList.add("open");
    setTimeout(() => document.addEventListener("click", this._onOutside), 0);
    document.addEventListener("keydown", this._onKey);
  }

  close() {
    this.menu.hidden = true;
    this.trigger.setAttribute("aria-expanded", "false");
    this.root.classList.remove("open");
    document.removeEventListener("click", this._onOutside);
    document.removeEventListener("keydown", this._onKey);
  }

  toggle() { this.menu.hidden ? this.open() : this.close(); }

  _onOutside(ev) { if (!this.root.contains(ev.target)) this.close(); }
  _onKey(ev) {
    if (ev.key === "Escape") { this.close(); this.trigger.focus(); }
  }

  reset() {
    for (const opt of this.options) {
      opt.classList.remove("active");
      opt.setAttribute("aria-checked", "false");
    }
    for (const sec of this.sections) sec.hidden = true;
    this.labelEl.textContent = this.initialLabel;
    this.root.classList.remove("has-selection");
  }

  select(type) {
    // Toggle off: clicking the currently-active option closes it.
    const currentActive = this.options.find((o) => o.classList.contains("active"));
    const isAlreadyActive = currentActive && currentActive.dataset.valveType === type;
    if (isAlreadyActive) {
      this.reset();
      this._showEmptyPromptIfNoneActive();
      this.close();
      return;
    }

    // No cross-category mutex: a salesperson configuring a valve and then
    // hitting "Configure matching actuator" needs BOTH sections visible. The
    // within-category section toggle (a few lines down) still ensures only one
    // valve type and one actuator type are open at a time.

    let chosenLabel = type;
    for (const opt of this.options) {
      const isActive = opt.dataset.valveType === type;
      opt.classList.toggle("active", isActive);
      opt.setAttribute("aria-checked", String(isActive));
      if (isActive) chosenLabel = opt.querySelector(".option-title").textContent.trim();
    }
    for (const sec of this.sections) {
      sec.hidden = sec.dataset.valveType !== type;
    }
    this.labelEl.textContent = chosenLabel;
    this.root.classList.add("has-selection");
    this.close();

    const prompt = document.getElementById("empty-prompt");
    if (prompt) prompt.hidden = true;
    const sec = this.sections.find((s) => s.dataset.valveType === type);
    if (sec) sec.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  _showEmptyPromptIfNoneActive() {
    const anyActive = TypePicker.instances.some((p) =>
      p.options.some((o) => o.classList.contains("active"))
    );
    if (!anyActive) {
      const prompt = document.getElementById("empty-prompt");
      if (prompt) prompt.hidden = false;
    }
  }
}

// The Accessories picker (.acc-picker) is driven by AccessoryPicker, not
// TypePicker — it has dropdowns, not type options.
document.querySelectorAll(".type-picker:not(.acc-picker)").forEach((p) => new TypePicker(p));

/* ---------- Cross-section: jump to the catalog-paired actuator ----------
   When a valve resolves, the result panel shows a "Configure matching
   actuator" button. Clicking it:
     1. Makes the target actuator section visible (via its TypePicker).
        BUT only if it isn't already the active option — TypePicker.select()
        toggles off if you re-pick the same type, which would close the panel
        we're trying to open.
     2. Sets the target cascade field (e.g. "model") to the paired value via
        Picker.setFieldValue, which auto-fills any single-option upstream
        fields and leaves the customer-driven attrs blank for the salesperson.
     3. Scrolls the section into view. */
async function viewMatchingActuator(targetType, targetField, value) {
  const targetSection = document.querySelector(
    `.valve-section[data-valve-type="${targetType}"]`
  );
  if (!targetSection) return;

  const category = targetSection.dataset.category;
  const typePicker = TypePicker.instances.find((p) => p.category === category);
  if (typePicker) {
    const activeOpt = typePicker.options.find((o) => o.classList.contains("active"));
    const alreadyOnTarget = activeOpt && activeOpt.dataset.valveType === targetType;
    if (!alreadyOnTarget) typePicker.select(targetType);
  }

  const picker = Picker.instances.get(targetType);
  if (picker) await picker.setFieldValue(targetField, value);

  targetSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ---------- Summary panel ----------
   Center band that shows the resolved valve + actuator codes once at least
   one has resolved. Listens for the custom `valve-selector:resolved` and
   `valve-selector:cleared` events emitted by each Picker. Tracks state by
   *category* (Valves vs Actuators) so when the user switches valve types or
   actuator types mid-flow, the corresponding card updates without leaking
   the prior selection. */
class SummaryPanel {
  constructor(rootEl) {
    this.root = rootEl;
    this.cards = new Map();  // category -> {cardEl, codeEl, nameEl}
    for (const cardEl of rootEl.querySelectorAll(".summary-card")) {
      const category = cardEl.dataset.summaryCategory;
      this.cards.set(category, {
        cardEl,
        codeEl: cardEl.querySelector(".summary-code"),
        nameEl: cardEl.querySelector(".summary-name"),
      });
    }
    // Track which catalog key currently owns each category card, so a
    // "cleared" event from a different (e.g. previously-selected) catalog
    // doesn't accidentally wipe the current card.
    this.activeKeyByCategory = new Map();

    document.addEventListener("valve-selector:resolved", (ev) => this._onResolved(ev.detail));
    document.addEventListener("valve-selector:cleared",  (ev) => this._onCleared(ev.detail));
  }

  _onResolved(detail) {
    const card = this.cards.get(detail.category);
    if (!card) return;
    this.activeKeyByCategory.set(detail.category, detail.key);

    card.codeEl.textContent = detail.primary ?? "—";

    // Compose a short descriptive name. Different shape per category:
    //   Valves    -> section label (e.g. "Butterfly Valve (Centric)")
    //   Actuators -> "<Model> · <Actuator description>" when both exist
    let name = detail.sectionLabel || "";
    if (detail.category === "Actuators") {
      const parts = [];
      if (detail.secondary) parts.push(detail.secondary);
      if (detail.actuatorName) parts.push(detail.actuatorName);
      if (parts.length) name = parts.join(" · ");
    }
    card.nameEl.textContent = name || "—";

    card.cardEl.hidden = false;
    this._refreshVisibility();
  }

  _onCleared(detail) {
    // Only clear if the cleared event came from the catalog currently shown
    // in this card. (When the user switches valve type via TypePicker, the
    // old picker section gets hidden but doesn't fire any event — the card
    // can stay populated until the new picker resolves.)
    if (this.activeKeyByCategory.get(detail.category) !== detail.key) return;
    const card = this.cards.get(detail.category);
    if (!card) return;
    card.cardEl.hidden = true;
    this.activeKeyByCategory.delete(detail.category);
    this._refreshVisibility();
  }

  _refreshVisibility() {
    const anyCardVisible = Array.from(this.cards.values()).some(c => !c.cardEl.hidden);
    this.root.hidden = !anyCardVisible;
  }
}

const summaryRoot = document.getElementById("workspace-summary");
if (summaryRoot) new SummaryPanel(summaryRoot);


/* Listens for the accessory selection broadcast and renders the
   accessories card inside the summary panel. Independent of SummaryPanel
   so the two concerns stay separate. */
class AccessorySummary {
  constructor() {
    this.cardEl = document.getElementById("summary-accessories");
    if (!this.cardEl) return;
    this.countEl = this.cardEl.querySelector(".summary-acc-count");
    this.listEl = this.cardEl.querySelector(".summary-acc-list");
    this.summaryRoot = document.getElementById("workspace-summary");
    document.addEventListener("accessories:selected-changed", (ev) => {
      this._onChange(ev.detail.rows);
    });
  }

  _onChange(rows) {
    if (!this.cardEl) return;
    const n = rows.length;
    if (this.countEl) this.countEl.textContent = String(n);
    if (this.listEl) {
      this.listEl.replaceChildren();
      if (n === 0) {
        this.listEl.textContent = "—";
      } else {
        // Each chip shows: family (small uppercase tag) + code (primary).
        // Tooltip still carries the first few attributes for hover detail.
        for (const r of rows) {
          const chip = document.createElement("span");
          chip.className = "summary-acc-chip";

          const familyEl = document.createElement("span");
          familyEl.className = "summary-acc-chip-family";
          familyEl.textContent = r.tag || r.family;
          chip.appendChild(familyEl);

          const codeEl = document.createElement("span");
          codeEl.className = "summary-acc-chip-code";
          codeEl.textContent = r.code;
          chip.appendChild(codeEl);

          chip.title = `${r.tag || r.family} — ${r.attrs.slice(0, 3).map(a => a.value).join(" · ")}`;
          this.listEl.appendChild(chip);
        }
      }
    }
    this.cardEl.hidden = n === 0;
    // Make sure the parent summary panel becomes visible when the user has
    // any accessories selected, even before a valve/actuator has resolved.
    if (this.summaryRoot && n > 0) {
      this.summaryRoot.hidden = false;
    } else if (this.summaryRoot && n === 0) {
      // If no valve/actuator card visible either, hide the whole summary.
      const anyOther = this.summaryRoot.querySelector(".summary-card:not(.summary-card--accessories):not([hidden])");
      if (!anyOther) this.summaryRoot.hidden = true;
    }
  }
}

/* ---------- Accessory picker (top-right, in the picker row) ----------
   Pick a Family to scope, then type-to-search the item (datalist). Selecting an
   item adds it — SINGLE-SELECT PER FAMILY: choosing another item in the same
   family replaces the prior one (a config needs one filter regulator, one
   positioner, etc.). Chosen accessories show as removable chips + a "Clear all";
   they broadcast via `accessories:selected-changed` (AccessorySummary renders
   them in the summary). Open/close handled here — excluded from TypePicker. */
class AccessoryPicker {
  constructor(root) {
    this.root = root;
    this.trigger = root.querySelector(".type-picker-trigger");
    this.menu = root.querySelector(".type-picker-menu");
    this.labelEl = root.querySelector(".type-picker-trigger-label");
    this.familySel = root.querySelector("#acc-family");
    this.searchInput = root.querySelector("#acc-search");
    this.datalist = root.querySelector("#acc-item-list");
    this.clearBtn = root.querySelector("#acc-clear");
    this.chipsEl = root.querySelector("#acc-selected-chips");
    this.countEl = root.querySelector("#acc-selected-count");
    this.byFamily = new Map();        // family (data key) -> [rows]
    this.byCode = new Map();          // code -> row
    this.byOptionValue = new Map();   // "CODE — label" -> code (datalist resolution)
    this.selected = new Map();        // family (data key) -> row  (one accessory per family)
    this.familyByKey = new Map();     // family key -> {key,tag,letter,label,count,pending}

    this._onOutside = (ev) => { if (!this.root.contains(ev.target)) this.close(); };
    this._onKey = (ev) => { if (ev.key === "Escape") this.close(); };
    this.trigger.addEventListener("click", (ev) => { ev.stopPropagation(); this.toggle(); });
    this.familySel.addEventListener("change", () => { this.searchInput.value = ""; this._onFamilyChange(); });
    // A datalist pick fires "input"; Enter on an exact match fires "change".
    this.searchInput.addEventListener("input", () => this._trySelectFromSearch());
    this.searchInput.addEventListener("change", () => this._trySelectFromSearch());
    this.clearBtn.addEventListener("click", () => this.clearAll());
    this._fetch();
  }

  open() {
    this.menu.hidden = false;
    this.root.classList.add("open");
    this.trigger.setAttribute("aria-expanded", "true");
    setTimeout(() => document.addEventListener("click", this._onOutside), 0);
    document.addEventListener("keydown", this._onKey);
    this.searchInput.focus();
  }
  close() {
    this.menu.hidden = true;
    this.root.classList.remove("open");
    this.trigger.setAttribute("aria-expanded", "false");
    document.removeEventListener("click", this._onOutside);
    document.removeEventListener("keydown", this._onKey);
  }
  toggle() { this.menu.hidden ? this.open() : this.close(); }

  async _fetch() {
    try {
      const data = await dataAPI.accessories();
      for (const r of (data.rows || [])) {
        this.byCode.set(r.code, r);
        if (!this.byFamily.has(r.family)) this.byFamily.set(r.family, []);
        this.byFamily.get(r.family).push(r);
      }
      this.familySel.replaceChildren();
      const famAll = document.createElement("option");
      famAll.value = "";
      famAll.textContent = "All families";
      this.familySel.appendChild(famAll);
      this.familyByKey.clear();
      for (const fam of (data.families || [])) {
        this.familyByKey.set(fam.key, fam);
        const o = document.createElement("option");
        o.value = fam.key;
        // Show BOTH abbreviations: "SV · S — Solenoid Valve (60)".
        const abbr = fam.letter ? `${fam.tag} · ${fam.letter}` : fam.tag;
        o.textContent = fam.pending
          ? `${abbr} — ${fam.label} (data pending)`
          : `${abbr} — ${fam.label} (${fam.count})`;
        this.familySel.appendChild(o);
      }
      this._fillDatalist();
    } catch (e) {
      if (this.labelEl) this.labelEl.textContent = "Accessories unavailable";
    }
  }

  /* React to a family change: a 'data pending' family (EVP, Plug, Direct Mount)
     has no items, so disable the search and show a pending hint instead of an
     empty type-ahead. */
  _onFamilyChange() {
    const fam = this.familyByKey.get(this.familySel.value);
    const pending = !!(fam && fam.pending);
    this.searchInput.disabled = pending;
    this.searchInput.placeholder = pending
      ? "Data pending — catalog coming soon"
      : "Type code or attribute…";
    this._fillDatalist();
  }

  /* Populate the type-ahead datalist with items in the chosen family (or all).
     Option value is "CODE — attr · attr", so typing a code OR an attribute
     substring narrows it; we map that value back to the code on selection. */
  _fillDatalist() {
    const fam = this.familySel.value;
    const rows = fam ? (this.byFamily.get(fam) || []) : [...this.byCode.values()];
    this.datalist.replaceChildren();
    this.byOptionValue.clear();
    for (const r of rows) {
      const label = r.attrs.slice(0, 4).map((a) => a.value).join(" · ");
      const val = label ? `${r.code} — ${label}` : r.code;
      this.byOptionValue.set(val, r.code);
      const o = document.createElement("option");
      o.value = val;
      this.datalist.appendChild(o);
    }
  }

  _trySelectFromSearch() {
    const raw = this.searchInput.value.trim();
    if (!raw) return;
    // Resolve: exact datalist value, else a bare code typed directly.
    let code = this.byOptionValue.get(raw);
    if (!code) {
      const head = raw.split(" — ")[0].trim();
      if (this.byCode.has(head)) code = head;
    }
    if (!code) return;                 // partial / no match yet — wait for more typing
    const row = this.byCode.get(code);
    if (!row) return;
    this.selected.set(row.family, row);   // SINGLE per family — replaces any prior
    this.searchInput.value = "";
    this._renderChips();
    this._broadcast();
  }

  clearAll() {
    if (this.selected.size === 0) return;
    this.selected.clear();
    this._renderChips();
    this._broadcast();
  }

  _renderChips() {
    this.chipsEl.replaceChildren();
    for (const [family, row] of this.selected) {
      const chip = document.createElement("span");
      chip.className = "acc-chip";
      const fam = document.createElement("span");
      fam.className = "acc-chip-fam";
      fam.textContent = row.tag || family;
      const c = document.createElement("span");
      c.className = "acc-chip-code";
      c.textContent = row.code;
      const x = document.createElement("button");
      x.type = "button";
      x.className = "acc-chip-x";
      x.setAttribute("aria-label", `Remove ${row.code}`);
      x.textContent = "×";
      x.addEventListener("click", (ev) => {
        ev.stopPropagation();
        this.selected.delete(family);
        this._renderChips();
        this._broadcast();
      });
      chip.append(fam, c, x);
      this.chipsEl.appendChild(chip);
    }
    const n = this.selected.size;
    if (this.countEl) this.countEl.textContent = String(n);
    if (this.clearBtn) this.clearBtn.hidden = n === 0;
    if (this.labelEl) this.labelEl.textContent = n ? `${n} selected` : "Add accessory";
    this.root.classList.toggle("has-selection", n > 0);
  }

  _broadcast() {
    document.dispatchEvent(new CustomEvent("accessories:selected-changed", {
      detail: { rows: [...this.selected.values()] },
    }));
  }
}

const accPickerRoot = document.getElementById("acc-picker");
const accPicker = accPickerRoot ? new AccessoryPicker(accPickerRoot) : null;
new AccessorySummary();

/* ---------- Combined product code ----------
   Assembles one orderable string matching the prior build's format:
     <Bare Valve Code> - <Actuator Code> - <Acc1>+<Acc2>+...
   Sections joined with " - " (space-hyphen-space); accessories joined with "+". */
class CombinedCode {
  constructor() {
    this.wrap = document.getElementById("summary-combined");
    this.codeEl = document.getElementById("summary-combined-code");
    this.copyBtn = document.getElementById("summary-combined-copy");
    if (!this.wrap || !this.codeEl) return;
    this.valve = null;        // {key, code}  (code = Bare Valve Code)
    this.actuator = null;     // {key, code}  (code = actuator Code)
    this.accessories = [];    // [code, ...]
    document.addEventListener("valve-selector:resolved", (e) => this._onResolved(e.detail));
    document.addEventListener("valve-selector:cleared", (e) => this._onCleared(e.detail));
    document.addEventListener("accessories:selected-changed", (e) => {
      // Product code uses each family's single LETTER (S/L/E/T/M/…); fall back
      // to the full accessory code for families with no letter (e.g. THW FOR MSD).
      this.accessories = (e.detail.rows || [])
        .map((r) => (r.letter && String(r.letter).trim()) ? String(r.letter).trim() : r.code)
        .filter(Boolean);
      this._render();
    });
    if (this.copyBtn) this.copyBtn.addEventListener("click", () => this._copy());
  }
  _onResolved(d) {
    // Valve part = Bare Valve Code (primary); Actuator part = its Code (primary).
    if (d.category === "Valves") this.valve = { key: d.key, code: d.primary };
    else if (d.category === "Actuators") this.actuator = { key: d.key, code: d.primary };
    this._render();
  }
  _onCleared(d) {
    if (d.category === "Valves" && this.valve && this.valve.key === d.key) this.valve = null;
    if (d.category === "Actuators" && this.actuator && this.actuator.key === d.key) this.actuator = null;
    this._render();
  }
  _render() {
    // <Bare Valve Code> - <Actuator Code> - <Acc1>+<Acc2>...
    const segs = [];
    if (this.valve && this.valve.code) segs.push(String(this.valve.code).trim());
    if (this.actuator && this.actuator.code) segs.push(String(this.actuator.code).trim());
    if (this.accessories.length) segs.push(this.accessories.map((c) => String(c).trim()).join("+"));
    if (!segs.length) { this.wrap.hidden = true; return; }
    this.codeEl.textContent = segs.join(" - ");
    this.wrap.hidden = false;
  }
  _copy() {
    const text = this.codeEl.textContent;
    if (!text || !navigator.clipboard) return;
    navigator.clipboard.writeText(text).then(() => {
      const prev = this.copyBtn.textContent;
      this.copyBtn.textContent = "Copied";
      setTimeout(() => { this.copyBtn.textContent = prev; }, 1200);
    }).catch(() => {});
  }
}
new CombinedCode();

/* ---------- Global reset (top-right) ----------
   Clears every valve/actuator cascade section AND all accessories at once. */
function globalReset() {
  for (const picker of Picker.instances.values()) {
    for (const f of picker.fields) f.value = "";
    picker.refreshOptions();
    picker.refreshResolution();
  }
  for (const tp of TypePicker.instances) tp.reset();
  const prompt = document.getElementById("empty-prompt");
  if (prompt) prompt.hidden = false;
  if (accPicker) accPicker.clearAll();
}

const globalResetBtn = document.getElementById("global-reset");
if (globalResetBtn) globalResetBtn.addEventListener("click", globalReset);
