"use strict";

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
    const url = `/api/${this.valveType}/options?picks=` + encodeURIComponent(JSON.stringify(picks));
    const resp = await fetch(url);
    if (!resp.ok) {
      this.statusEl.textContent = "Server error loading options.";
      return;
    }
    const opts = await resp.json();
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
    const url = `/api/${this.valveType}/resolve?picks=` + encodeURIComponent(JSON.stringify(picks));
    const resp = await fetch(url);
    const data = await resp.json();
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

document.querySelectorAll(".type-picker").forEach((p) => new TypePicker(p));

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

/* ---------- Accessory browser ----------
   Multi-select list of all accessories — NO recommendation, no cascade. The
   user explicitly browses, ticks the items they want, and the summary panel
   echoes the running selection. Filtering by family + free-text search is
   client-side (the full list is small enough to ship once).

   Selection state lives in `selected` (a Set of codes) and is rebroadcast
   on every change via `accessories:selected-changed`, which a dedicated
   AccessorySummary instance below listens for and renders into the
   summary panel. */
class AccessoryBrowser {
  constructor(rootEl) {
    this.root = rootEl;
    this.listEl = rootEl.querySelector("#accessories-list");
    this.familyFilterEl = rootEl.querySelector("#accessories-family-filter");
    this.searchInputEl = rootEl.querySelector("#accessories-search-input");
    this.selectedCountEl = rootEl.querySelector("#accessories-selected-count");
    this.clearBtnEl = rootEl.querySelector("#accessories-clear-btn");

    this.allRows = [];      // [{code, family, attrs}]
    this.families = [];     // [{name, count}]
    this.selected = new Set();
    this.familyFilter = "";
    this.searchText = "";
    // Lookup maps for the one-per-family constraint:
    //   codeToRow  — O(1) lookup of {family, attrs} when we only have a code
    //   itemEls    — DOM refs for currently-rendered rows, so when the user
    //                picks a new item we can uncheck the prior same-family
    //                row's checkbox AND remove its visual selected state.
    this.codeToRow = new Map();
    this.itemEls = new Map();

    if (this.familyFilterEl) {
      this.familyFilterEl.addEventListener("change", () => {
        this.familyFilter = this.familyFilterEl.value;
        this._render();
      });
    }
    if (this.searchInputEl) {
      this.searchInputEl.addEventListener("input", () => {
        this.searchText = this.searchInputEl.value.trim().toLowerCase();
        this._render();
      });
    }
    if (this.clearBtnEl) {
      this.clearBtnEl.addEventListener("click", () => this._clearAll());
    }

    this._fetch();
  }

  async _fetch() {
    try {
      const resp = await fetch("/api/accessories/list");
      const data = await resp.json();
      this.allRows = data.rows || [];
      this.families = data.families || [];
      this.codeToRow.clear();
      for (const r of this.allRows) this.codeToRow.set(r.code, r);
      this._populateFamilyFilter();
      this._render();
    } catch (e) {
      if (this.listEl) {
        this.listEl.textContent = "Failed to load accessories.";
      }
    }
  }

  _populateFamilyFilter() {
    if (!this.familyFilterEl) return;
    for (const fam of this.families) {
      const opt = document.createElement("option");
      opt.value = fam.name;
      opt.textContent = `${fam.name} (${fam.count})`;
      this.familyFilterEl.appendChild(opt);
    }
  }

  _matches(row) {
    if (this.familyFilter && row.family !== this.familyFilter) return false;
    if (!this.searchText) return true;
    // Search in code + family + any attribute value
    if (row.code.toLowerCase().includes(this.searchText)) return true;
    if (row.family.toLowerCase().includes(this.searchText)) return true;
    for (const a of row.attrs) {
      if (String(a.value).toLowerCase().includes(this.searchText)) return true;
    }
    return false;
  }

  _render() {
    if (!this.listEl) return;
    this.listEl.replaceChildren();
    this.itemEls.clear();

    const filtered = this.allRows.filter((r) => this._matches(r));
    if (filtered.length === 0) {
      const empty = document.createElement("div");
      empty.className = "accessories-empty";
      empty.textContent = "No accessories match the current filter.";
      this.listEl.appendChild(empty);
      this._updateSelectedSummary();
      return;
    }

    // Group filtered rows by family — preserves the natural grouping the
    // source file already organizes data by.
    const byFamily = new Map();
    for (const r of filtered) {
      if (!byFamily.has(r.family)) byFamily.set(r.family, []);
      byFamily.get(r.family).push(r);
    }

    for (const [familyName, rows] of byFamily) {
      const group = document.createElement("div");
      group.className = "acc-group";

      const groupHead = document.createElement("div");
      groupHead.className = "acc-group-head";
      const groupName = document.createElement("span");
      groupName.className = "acc-group-name";
      groupName.textContent = familyName;
      const groupCount = document.createElement("span");
      groupCount.className = "acc-group-count";
      groupCount.textContent = `${rows.length} item${rows.length === 1 ? "" : "s"}`;
      groupHead.appendChild(groupName);
      groupHead.appendChild(groupCount);
      group.appendChild(groupHead);

      for (const row of rows) {
        group.appendChild(this._renderRow(row));
      }
      this.listEl.appendChild(group);
    }

    this._updateSelectedSummary();
  }

  _renderRow(row) {
    const item = document.createElement("label");
    item.className = "acc-item";
    item.setAttribute("role", "listitem");
    if (this.selected.has(row.code)) item.classList.add("acc-item--selected");

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.className = "acc-checkbox";
    cb.checked = this.selected.has(row.code);
    cb.addEventListener("change", () => {
      if (cb.checked) {
        // One-per-family constraint: any prior selection in this row's
        // family gets deselected when a new one is picked.
        this._deselectSameFamily(row.family, row.code);
        this.selected.add(row.code);
        item.classList.add("acc-item--selected");
      } else {
        this.selected.delete(row.code);
        item.classList.remove("acc-item--selected");
      }
      this._updateSelectedSummary();
      this._broadcast();
    });

    // Register so _deselectSameFamily can uncheck this row's DOM later if
    // a sibling in the same family is selected.
    this.itemEls.set(row.code, { item, cb });

    const body = document.createElement("span");
    body.className = "acc-item-body";

    const code = document.createElement("span");
    code.className = "acc-item-code";
    code.textContent = row.code;
    body.appendChild(code);

    if (row.attrs.length) {
      const attrs = document.createElement("span");
      attrs.className = "acc-item-attrs";
      // Compact attribute summary: first 4 attrs joined with " · "
      const shown = row.attrs.slice(0, 4).map((a) => a.value).join(" · ");
      attrs.textContent = shown;
      body.appendChild(attrs);
    }

    item.appendChild(cb);
    item.appendChild(body);
    return item;
  }

  /* Enforce "at most one selected per family". Called BEFORE adding the
     new selection. Removes any currently-selected code in the same family
     (other than `keepCode`) from `this.selected`, and — if that code's
     DOM row is currently rendered — unchecks its checkbox and removes the
     selected highlight. Off-screen rows still get removed from state, so
     re-rendering them later picks up the correct unchecked state. */
  _deselectSameFamily(family, keepCode) {
    const toRemove = [];
    for (const code of this.selected) {
      if (code === keepCode) continue;
      const r = this.codeToRow.get(code);
      if (r && r.family === family) toRemove.push(code);
    }
    for (const code of toRemove) {
      this.selected.delete(code);
      const els = this.itemEls.get(code);
      if (els) {
        els.cb.checked = false;
        els.item.classList.remove("acc-item--selected");
      }
    }
  }

  _updateSelectedSummary() {
    const n = this.selected.size;
    if (this.selectedCountEl) {
      this.selectedCountEl.textContent = `${n} selected`;
    }
    if (this.clearBtnEl) {
      this.clearBtnEl.hidden = n === 0;
    }
  }

  _clearAll() {
    this.selected.clear();
    // Uncheck all visible checkboxes + remove visual selected state
    for (const cb of this.listEl.querySelectorAll(".acc-checkbox")) {
      cb.checked = false;
    }
    for (const item of this.listEl.querySelectorAll(".acc-item--selected")) {
      item.classList.remove("acc-item--selected");
    }
    this._updateSelectedSummary();
    this._broadcast();
  }

  _broadcast() {
    // Push the current selection out for the summary panel to render.
    // Look up the full row for each selected code so the summary can
    // display family + a short label, not just the bare code.
    const selectedRows = this.allRows.filter((r) => this.selected.has(r.code));
    document.dispatchEvent(new CustomEvent("accessories:selected-changed", {
      detail: { rows: selectedRows },
    }));
  }
}

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
          familyEl.textContent = r.family;
          chip.appendChild(familyEl);

          const codeEl = document.createElement("span");
          codeEl.className = "summary-acc-chip-code";
          codeEl.textContent = r.code;
          chip.appendChild(codeEl);

          chip.title = `${r.family} — ${r.attrs.slice(0, 3).map(a => a.value).join(" · ")}`;
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

const accessoriesRoot = document.getElementById("workspace-accessories");
if (accessoriesRoot && accessoriesRoot.querySelector("#accessories-list")) {
  new AccessoryBrowser(accessoriesRoot);
}
new AccessorySummary();
