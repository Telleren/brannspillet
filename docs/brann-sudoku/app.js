const DATASETS = {
  all: {
    label: "Full historikk",
    criteriaUrl: "../shared/grid-criteria-index.json",
    factsUrl: "../shared/player-facts.json",
  },
  modern: {
    label: "Moderne (2000-)",
    criteriaUrl: "../shared/grid-criteria-index-modern.json",
    factsUrl: "../shared/player-facts-modern.json",
  },
};

const state = {
  criteriaIndex: null,
  playerFacts: null,
  datasetMode: "all",
  fixedCriterionDisplays: new Map(),
  entityDisplays: new Map(),
  playerDisplays: new Map(),
  criterionPlayerSets: new Map(),
  editors: {},
  selectedCell: null,
  randomBoardNotice: null,
};

const editorSlots = [
  { id: "row-0", axis: "row", index: 0, label: "Rad 1" },
  { id: "row-1", axis: "row", index: 1, label: "Rad 2" },
  { id: "row-2", axis: "row", index: 2, label: "Rad 3" },
  { id: "col-0", axis: "column", index: 0, label: "Kolonne 1" },
  { id: "col-1", axis: "column", index: 1, label: "Kolonne 2" },
  { id: "col-2", axis: "column", index: 2, label: "Kolonne 3" },
];

const ruleKinds = [
  ["fixed", "Ferdig kategori"],
  ["metric", "Antall / terskel"],
  ["date", "Dato / år"],
  ["age", "Alder"],
  ["setCount", "Antall sesonger/typer"],
  ["name", "Navn"],
];

const numericOperators = [
  [">", "Mer enn"],
  [">=", "Minst"],
  ["=", "Nøyaktig"],
  ["<", "Mindre enn"],
  ["<=", "Høyst"],
  [">player", "Flere enn spiller"],
  ["<player", "Færre enn spiller"],
];

const setCountOptions = [
  ["brannYears", "Spilt i minst X sesonger"],
  ["decadesPlayed", "Spilt i minst X tiår"],
  ["shirtNumbers", "Brukt minst X draktnumre"],
  ["competitionsPlayed", "Spilt i minst X turneringer"],
  ["competitionsScored", "Scoret i minst X turneringer"],
  ["coachesPlayed", "Spilt under minst X trenere"],
];

const nameModes = [
  ["firstInitial", "Fornavn begynner på"],
  ["lastInitial", "Etternavn begynner på"],
  ["nameLength", "Navn har minst X bokstaver"],
];

const wishlistCoverage = [
  ["ok", "Antall kamper/mål", "Støtter terskel, nøyaktig verdi og sammenligning mot spiller."],
  ["ok", "Straffemål og røde kort", "Støtter totale straffemål og røde kort totalt, i turneringer og på stadioner."],
  ["ok", "Turnering, serie, motstander, trener", "Støtter turneringer, samlede seriekategorier og trenere. Motstanderklubb er avgrenset til scoret mot."],
  ["ok", "År, tiår, debut/siste kamp", "Støtter spilt i år/tiår, debutår/periode og siste kamp-år/periode."],
  ["ok", "Draktnummer og posisjon", "Støtter observerte draktnumre og brede Branntall-roller."],
  ["ok", "Spilt med spiller", "Støtter antall kamper samtidig med annen Brann-spiller."],
  ["ok", "Navn", "Støtter forbokstav i fornavn/etternavn og enkel navnelengde."],
  ["partial", "Alder", "Støtter alder ved debut og siste Brann-kamp når fødselsdato finnes."],
  ["partial", "Geografi", "Støtter kamp i land via stadionland. By finnes ikke strukturert ennå."],
  ["ok", "Brann-meritter", "Støtter seriegull, seriesølv, seriebronse, seriemedalje, opprykk, nedrykk, cupmester og tapt cupfinale fra manuell merittkilde."],
  ["partial", "Cupfinale/europacup", "Støtter cupfinale, semifinale, Europa-gruppe/ligafase og Europa-kvalik."],
  ["no", "Landskamper/landslagsturneringer", "Ikke i Branntall-datasettet."],
  ["no", "Andre klubber/ligaer/overganger", "Krever ekstern karriere- og overgangsdata."],
  ["no", "Egenutviklet/lokal bakgrunn", "Krever manuell bakgrunnsberiking."],
  ["no", "Alder ved siste mål/resultatparametre", "Må berikes i grid-eksporten før UI-et kan validere det trygt."],
];

function $(selector) {
  return document.querySelector(selector);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function normalizeText(value) {
  return String(value || "")
    .toLocaleLowerCase("nb")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replaceAll("æ", "ae")
    .replaceAll("ø", "o")
    .replaceAll("å", "a")
    .trim();
}

function playerName(playerId) {
  return state.criteriaIndex.entities.players[playerId]?.name || playerId;
}

function playerSort(a, b) {
  const playerA = state.criteriaIndex.entities.players[a];
  const playerB = state.criteriaIndex.entities.players[b];
  const keyA = playerA?.searchText || playerA?.name || a;
  const keyB = playerB?.searchText || playerB?.name || b;
  return keyA.localeCompare(keyB, "nb") || a.localeCompare(b);
}

function allPlayerIds() {
  return Object.keys(state.criteriaIndex.entities.players);
}

function optionDisplay(label, count, id) {
  return `${label} (${count}) · ${id}`;
}

function populateDatalists() {
  const fixedList = $("#fixedCriteriaList");
  const entityList = $("#entityList");
  const playerList = $("#playerList");

  fixedList.innerHTML = "";
  entityList.innerHTML = "";
  playerList.innerHTML = "";
  state.fixedCriterionDisplays.clear();
  state.entityDisplays.clear();
  state.playerDisplays.clear();
  state.criterionPlayerSets.clear();

  const criteria = Object.values(state.criteriaIndex.criteria)
    .sort((a, b) => a.label.localeCompare(b.label, "nb") || a.id.localeCompare(b.id));

  for (const criterion of criteria) {
    const display = displayForCriterion(criterion);
    state.fixedCriterionDisplays.set(display, criterion.id);
    fixedList.append(el("option", "", display));
  }

  for (const [entityType, entities] of Object.entries(state.criteriaIndex.entities)) {
    if (entityType === "players") continue;

    for (const entity of Object.values(entities)) {
      const label = entity.name || entity.label || entity.id;
      const display = `${label} · ${entityType}:${entity.id}`;
      state.entityDisplays.set(display, { entityType, entityId: String(entity.id) });
      entityList.append(el("option", "", display));
    }
  }

  const players = Object.values(state.criteriaIndex.entities.players)
    .sort((a, b) => (a.searchText || a.name).localeCompare(b.searchText || b.name, "nb"));

  for (const player of players) {
    const display = `${player.name} · ${player.id}`;
    state.playerDisplays.set(display, player.id);
    playerList.append(el("option", "", display));
  }
}

function selectOptions(options, selected) {
  return options.map(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = value === selected;
    return option;
  });
}

function makeLabeledControl(labelText, control, wide = false) {
  const label = el("label", wide ? "wide" : "");
  label.append(labelText, control);
  return label;
}

function createEditor(slot) {
  const wrapper = el("section", "criterion-editor");
  wrapper.dataset.slotId = slot.id;

  const title = el("div", "editor-title");
  const titleText = el("div", "editor-title-text");
  titleText.append(
    el("span", "", slot.label),
    el("span", "", slot.axis === "row" ? "Rad" : "Kolonne")
  );

  const lock = document.createElement("input");
  lock.type = "checkbox";
  lock.className = "lock-input";
  const lockLabel = el("label", "lock-toggle");
  lockLabel.append(lock, "Lås");
  title.append(titleText, lockLabel);

  const kind = document.createElement("select");
  kind.className = "kind-select";
  kind.append(...selectOptions(ruleKinds, "fixed"));

  const controls = el("div", "control-grid");
  const preview = el("div", "rule-preview", "Ingen kategori valgt.");

  wrapper.append(
    title,
    makeLabeledControl("Type", kind, true),
    controls,
    preview
  );

  state.editors[slot.id] = {
    slot,
    wrapper,
    kind,
    lock,
    controls,
    preview,
    fields: {},
  };

  kind.addEventListener("change", () => {
    state.randomBoardNotice = null;
    renderEditorControls(slot.id);
    renderBoard();
  });
  lock.addEventListener("change", () => {
    state.randomBoardNotice = null;
    wrapper.classList.toggle("is-locked", lock.checked);
    renderBoard();
  });

  renderEditorControls(slot.id);

  return wrapper;
}

function addChangeListener(editor) {
  for (const field of Object.values(editor.fields)) {
    field.addEventListener("input", () => {
      state.randomBoardNotice = null;
      renderBoard();
    });
    field.addEventListener("change", () => {
      state.randomBoardNotice = null;
      renderBoard();
    });
  }
}

function metricFamilyOptions() {
  return Object.entries(state.criteriaIndex.metricFamilies)
    .filter(([, family]) => family.supportsThreshold)
    .sort(([, a], [, b]) => a.label.localeCompare(b.label, "nb"))
    .map(([id, family]) => [id, family.label]);
}

function renderEditorControls(slotId) {
  const editor = state.editors[slotId];
  editor.controls.innerHTML = "";
  editor.fields = {};

  const kind = editor.kind.value;

  if (kind === "fixed") {
    const input = document.createElement("input");
    input.setAttribute("list", "fixedCriteriaList");
    input.placeholder = "Søk: Vålerenga, cupfinale, draktnummer 10...";
    editor.fields.fixed = input;
    editor.controls.append(makeLabeledControl("Kategori", input, true));
  }

  if (kind === "metric") {
    const family = document.createElement("select");
    family.append(...selectOptions(metricFamilyOptions(), "appearancesTotal"));

    const entity = document.createElement("input");
    entity.setAttribute("list", "entityList");
    entity.placeholder = "Velg motstander, turnering, seriekategori, trener eller spiller";

    const operator = document.createElement("select");
    operator.append(...selectOptions(numericOperators, ">"));

    const value = document.createElement("input");
    value.type = "number";
    value.min = "0";
    value.value = "10";

    const comparePlayer = document.createElement("input");
    comparePlayer.setAttribute("list", "playerList");
    comparePlayer.placeholder = "Velg spiller";

    editor.fields = { family, entity, operator, value, comparePlayer };
    editor.controls.append(
      makeLabeledControl("Statistikk", family, true),
      makeLabeledControl("Enhet", entity, true),
      makeLabeledControl("Operator", operator),
      makeLabeledControl("Tall", value),
      makeLabeledControl("Sammenlign med", comparePlayer, true)
    );
  }

  if (kind === "date") {
    const field = document.createElement("select");
    field.append(
      ...selectOptions([
        ["firstBrannMatchDate", "Debutdato"],
        ["lastBrannMatchDate", "Siste Brann-kamp"],
      ], "firstBrannMatchDate")
    );

    const mode = document.createElement("select");
    mode.append(
      ...selectOptions([
        ["year", "I år"],
        ["from", "Fra og med år"],
        ["to", "Til og med år"],
        ["range", "I periode"],
      ], "year")
    );

    const year = document.createElement("input");
    year.type = "number";
    year.value = "2000";

    const endYear = document.createElement("input");
    endYear.type = "number";
    endYear.value = "2026";

    editor.fields = { field, mode, year, endYear };
    editor.controls.append(
      makeLabeledControl("Dato", field),
      makeLabeledControl("Regel", mode),
      makeLabeledControl("År", year),
      makeLabeledControl("Til år", endYear)
    );
  }

  if (kind === "age") {
    const field = document.createElement("select");
    field.append(
      ...selectOptions([
        ["firstBrannMatchDate", "Alder ved debut"],
        ["lastBrannMatchDate", "Alder ved siste kamp"],
      ], "firstBrannMatchDate")
    );

    const operator = document.createElement("select");
    operator.append(...selectOptions(numericOperators.slice(0, 5), "<"));

    const value = document.createElement("input");
    value.type = "number";
    value.min = "0";
    value.value = "21";

    editor.fields = { field, operator, value };
    editor.controls.append(
      makeLabeledControl("Alderstype", field, true),
      makeLabeledControl("Operator", operator),
      makeLabeledControl("Alder", value)
    );
  }

  if (kind === "setCount") {
    const setName = document.createElement("select");
    setName.append(...selectOptions(setCountOptions, "brannYears"));

    const value = document.createElement("input");
    value.type = "number";
    value.min = "1";
    value.value = "3";

    editor.fields = { setName, value };
    editor.controls.append(
      makeLabeledControl("Kategori", setName, true),
      makeLabeledControl("Minst", value)
    );
  }

  if (kind === "name") {
    const mode = document.createElement("select");
    mode.append(...selectOptions(nameModes, "firstInitial"));

    const text = document.createElement("input");
    text.maxLength = 1;
    text.value = "A";

    const length = document.createElement("input");
    length.type = "number";
    length.min = "1";
    length.value = "12";

    editor.fields = { mode, text, length };
    editor.controls.append(
      makeLabeledControl("Navneregel", mode, true),
      makeLabeledControl("Bokstav", text),
      makeLabeledControl("Lengde", length)
    );
  }

  addChangeListener(editor);
}

function compare(value, operator, threshold) {
  if (operator === ">") return value > threshold;
  if (operator === ">=") return value >= threshold;
  if (operator === "=") return value === threshold;
  if (operator === "<") return value < threshold;
  if (operator === "<=") return value <= threshold;
  return false;
}

function metricValues(familyId, entityId = null) {
  const metric = state.criteriaIndex.metrics[familyId] || {};
  if (entityId === null) return metric;
  return metric[entityId] || {};
}

function metricLabel(familyId, entityId) {
  const family = state.criteriaIndex.metricFamilies[familyId];
  if (!family) return "Ukjent statistikk";

  if (!family.entityType) return family.label;

  const entity = state.criteriaIndex.entities[family.entityType]?.[entityId];
  const entityName = entity?.name || entity?.label || entityId || "mangler enhet";
  return `${family.label}: ${entityName}`;
}

function resolveEntity(display, expectedType) {
  const resolved = state.entityDisplays.get(display);
  if (!resolved) return null;
  if (expectedType && resolved.entityType !== expectedType) return null;
  return resolved.entityId;
}

function resolvePlayer(display) {
  return state.playerDisplays.get(display) || null;
}

function setFromArray(values) {
  return new Set(values || []);
}

function criterionPlayerSet(criterion) {
  if (!state.criterionPlayerSets.has(criterion.id)) {
    state.criterionPlayerSets.set(
      criterion.id,
      setFromArray(criterion.players)
    );
  }
  return state.criterionPlayerSets.get(criterion.id);
}

function intersectionHasAtLeast(a, b, minimum) {
  const small = a.size <= b.size ? a : b;
  const large = a.size <= b.size ? b : a;
  let count = 0;

  for (const item of small) {
    if (!large.has(item)) continue;
    count += 1;
    if (count >= minimum) return true;
  }

  return false;
}

function intersectionCount(a, b) {
  const small = a.size <= b.size ? a : b;
  const large = a.size <= b.size ? b : a;
  let count = 0;

  for (const item of small) {
    if (large.has(item)) count += 1;
  }

  return count;
}

function intersectionFitsRange(a, b, minimum, maximum) {
  const count = intersectionCount(a, b);
  return count >= minimum && count <= maximum;
}

function cellPlayerSets(assignments) {
  const result = [];

  for (let rowIndex = 0; rowIndex < 3; rowIndex += 1) {
    for (let colIndex = 0; colIndex < 3; colIndex += 1) {
      const rowRule = assignments[`row-${rowIndex}`];
      const colRule = assignments[`col-${colIndex}`];

      if (rowRule?.ok && colRule?.ok) {
        result.push(intersectSets(rowRule.players, colRule.players));
      }
    }
  }

  return result;
}

function cellPlayerSetsAreDisjoint(assignments) {
  const seenPlayerIds = new Set();

  for (const playerSet of cellPlayerSets(assignments)) {
    for (const playerId of playerSet) {
      if (seenPlayerIds.has(playerId)) return false;
      seenPlayerIds.add(playerId);
    }
  }

  return true;
}

function shuffle(values) {
  const copy = [...values];

  for (let index = copy.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[swapIndex]] = [copy[swapIndex], copy[index]];
  }

  return copy;
}

function randomizableCriteria(minimum) {
  return Object.values(state.criteriaIndex.criteria)
    .filter((criterion) => (
      Array.isArray(criterion.players)
      && criterion.players.length >= minimum
      && criterion.players.length < state.criteriaIndex.playerCount
    ));
}

function ruleFromCriterion(criterion) {
  return {
    ok: true,
    label: criterion.label,
    players: criterionPlayerSet(criterion),
    count: criterion.count,
    criterionId: criterion.id,
    criterion,
  };
}

function oppositeSlotIds(slot) {
  const prefix = slot.axis === "row" ? "col" : "row";
  return [0, 1, 2].map((index) => `${prefix}-${index}`);
}

function ruleFitsSlot(slot, rule, assignments, minimum, maximum) {
  const fitsCounts = oppositeSlotIds(slot).every((oppositeSlotId) => {
    const oppositeRule = assignments[oppositeSlotId];
    if (!oppositeRule?.ok) return true;
    return intersectionFitsRange(
      rule.players,
      oppositeRule.players,
      minimum,
      maximum
    );
  });

  if (!fitsCounts) return false;

  return cellPlayerSetsAreDisjoint({
    ...assignments,
    [slot.id]: rule,
  });
}

function validateAssignments(assignments, minimum, maximum) {
  for (let rowIndex = 0; rowIndex < 3; rowIndex += 1) {
    for (let colIndex = 0; colIndex < 3; colIndex += 1) {
      const rowRule = assignments[`row-${rowIndex}`];
      const colRule = assignments[`col-${colIndex}`];
      if (!rowRule?.ok || !colRule?.ok) continue;
      if (!intersectionFitsRange(
        rowRule.players,
        colRule.players,
        minimum,
        maximum
      )) {
        return false;
      }
    }
  }

  return cellPlayerSetsAreDisjoint(assignments);
}

function unlockedSlotsOrdered(assignments) {
  return editorSlots
    .filter((slot) => !assignments[slot.id])
    .sort((a, b) => {
      const aLockedOpposites = oppositeSlotIds(a)
        .filter((slotId) => assignments[slotId]).length;
      const bLockedOpposites = oppositeSlotIds(b)
        .filter((slotId) => assignments[slotId]).length;
      return bLockedOpposites - aLockedOpposites;
    });
}

function findRandomBoard(minimum, maximum, lockedRules = {}) {
  const candidates = randomizableCriteria(minimum);
  const maxAttempts = 20000;

  if (!validateAssignments(lockedRules, minimum, maximum)) return null;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const assignments = { ...lockedRules };
    const usedCriterionIds = new Set(
      Object.values(assignments)
        .map((rule) => rule.criterionId)
        .filter(Boolean)
    );
    let failed = false;

    for (const slot of unlockedSlotsOrdered(assignments)) {
      const matching = shuffle(candidates)
        .filter((criterion) => !usedCriterionIds.has(criterion.id))
        .map(ruleFromCriterion)
        .filter((rule) => ruleFitsSlot(
          slot,
          rule,
          assignments,
          minimum,
          maximum
        ));

      if (!matching.length) {
        failed = true;
        break;
      }

      const rule = matching[0];
      assignments[slot.id] = rule;
      usedCriterionIds.add(rule.criterionId);
    }

    if (!failed && validateAssignments(assignments, minimum, maximum)) {
      return { assignments, minimum };
    }
  }

  return null;
}

function displayForCriterion(criterion) {
  return optionDisplay(criterion.label, criterion.count, criterion.id);
}

function setEditorFixedCriterion(slotId, criterion) {
  const editor = state.editors[slotId];
  editor.kind.value = "fixed";
  renderEditorControls(slotId);
  editor.fields.fixed.value = displayForCriterion(criterion);
}

function evaluateFixed(editor) {
  const display = editor.fields.fixed.value;
  const criterionId = state.fixedCriterionDisplays.get(display);
  const criterion = state.criteriaIndex.criteria[criterionId];

  if (!criterion) {
    return missingRule("Velg et ferdig kriterium.");
  }

  return {
    ok: true,
    label: criterion.label,
    players: setFromArray(criterion.players),
    count: criterion.count,
    criterionId,
  };
}

function evaluateMetric(editor) {
  const familyId = editor.fields.family.value;
  const family = state.criteriaIndex.metricFamilies[familyId];

  if (!family) return missingRule("Velg statistikk.");

  const entityId = family.entityType
    ? resolveEntity(editor.fields.entity.value, family.entityType)
    : null;

  if (family.entityType && !entityId) {
    return missingRule(`Velg enhet av typen ${family.entityType}.`);
  }

  const operator = editor.fields.operator.value;
  const values = metricValues(familyId, entityId);
  let threshold = Number(editor.fields.value.value || 0);
  let thresholdLabel = threshold;

  if (operator === ">player" || operator === "<player") {
    const playerId = resolvePlayer(editor.fields.comparePlayer.value);
    if (!playerId) return missingRule("Velg spiller å sammenligne med.");
    threshold = Number(values[playerId] || 0);
    thresholdLabel = `${playerName(playerId)} (${threshold})`;
  }

  const simpleOperator = operator === ">player" ? ">" : operator === "<player" ? "<" : operator;
  const players = allPlayerIds().filter((playerId) => {
    const value = Number(values[playerId] || 0);
    return compare(value, simpleOperator, threshold);
  });

  const label = `${metricLabel(familyId, entityId)} ${operatorText(operator)} ${thresholdLabel}`;

  return {
    ok: true,
    label,
    players: setFromArray(players),
    count: players.length,
  };
}

function operatorText(operator) {
  return Object.fromEntries(numericOperators)[operator] || operator;
}

function evaluateDate(editor) {
  const field = editor.fields.field.value;
  const mode = editor.fields.mode.value;
  const year = Number(editor.fields.year.value || 0);
  const endYear = Number(editor.fields.endYear.value || 0);
  const fieldLabel = field === "firstBrannMatchDate" ? "Debut" : "Siste Brann-kamp";

  const players = allPlayerIds().filter((playerId) => {
    const value = state.playerFacts.players[playerId]?.[field];
    if (!value) return false;
    const valueYear = Number(value.slice(0, 4));

    if (mode === "year") return valueYear === year;
    if (mode === "from") return valueYear >= year;
    if (mode === "to") return valueYear <= year;
    if (mode === "range") return valueYear >= year && valueYear <= endYear;
    return false;
  });

  const suffix = {
    year: `i ${year}`,
    from: `fra og med ${year}`,
    to: `til og med ${year}`,
    range: `i perioden ${year}-${endYear}`,
  }[mode];

  return {
    ok: true,
    label: `${fieldLabel} ${suffix}`,
    players: setFromArray(players),
    count: players.length,
  };
}

function ageAt(birthdate, matchDate) {
  if (!birthdate || !matchDate) return null;
  const birth = new Date(`${birthdate}T00:00:00Z`);
  const match = new Date(`${matchDate}T00:00:00Z`);
  let age = match.getUTCFullYear() - birth.getUTCFullYear();
  const beforeBirthday =
    match.getUTCMonth() < birth.getUTCMonth()
    || (
      match.getUTCMonth() === birth.getUTCMonth()
      && match.getUTCDate() < birth.getUTCDate()
    );
  if (beforeBirthday) age -= 1;
  return Number.isFinite(age) ? age : null;
}

function evaluateAge(editor) {
  const field = editor.fields.field.value;
  const operator = editor.fields.operator.value;
  const threshold = Number(editor.fields.value.value || 0);
  const labelBase = field === "firstBrannMatchDate" ? "Alder ved debut" : "Alder ved siste kamp";

  const players = allPlayerIds().filter((playerId) => {
    const fact = state.playerFacts.players[playerId];
    const age = ageAt(fact?.birthdate, fact?.[field]);
    return age !== null && compare(age, operator, threshold);
  });

  return {
    ok: true,
    label: `${labelBase} ${operatorText(operator)} ${threshold}`,
    players: setFromArray(players),
    count: players.length,
  };
}

function countSetForPlayer(playerId, setName) {
  const fact = state.playerFacts.players[playerId];
  if (!fact) return 0;

  if (setName === "brannYears") return (fact.brannYears || []).length;
  if (setName === "decadesPlayed") return (fact.sets.decadesPlayed || []).length;
  if (setName === "shirtNumbers") return (fact.sets.shirtNumbers || []).length;
  if (setName === "competitionsPlayed") return (fact.sets.competitionsPlayed || []).length;
  if (setName === "coachesPlayed") return (fact.sets.coachesPlayed || []).length;

  if (setName === "competitionsScored") {
    let count = 0;
    for (const values of Object.values(state.criteriaIndex.metrics.goalsByCompetition || {})) {
      if (Number(values[playerId] || 0) > 0) count += 1;
    }
    return count;
  }

  return 0;
}

function evaluateSetCount(editor) {
  const setName = editor.fields.setName.value;
  const threshold = Number(editor.fields.value.value || 1);
  const label = Object.fromEntries(setCountOptions)[setName] || "Antall";

  const players = allPlayerIds().filter((playerId) => (
    countSetForPlayer(playerId, setName) >= threshold
  ));

  return {
    ok: true,
    label: label.replace("X", threshold),
    players: setFromArray(players),
    count: players.length,
  };
}

function evaluateName(editor) {
  const mode = editor.fields.mode.value;
  const letter = normalizeText(editor.fields.text.value).slice(0, 1).toUpperCase();
  const length = Number(editor.fields.length.value || 1);
  const facts = state.playerFacts.players;

  const players = allPlayerIds().filter((playerId) => {
    const name = facts[playerId]?.name || "";
    const parts = name.trim().split(/\s+/).filter(Boolean);
    const first = normalizeText(parts[0] || "").slice(0, 1).toUpperCase();
    const last = normalizeText(parts.at(-1) || "").slice(0, 1).toUpperCase();
    const compactLength = normalizeText(name).replace(/\s+/g, "").length;

    if (mode === "firstInitial") return first === letter;
    if (mode === "lastInitial") return last === letter;
    if (mode === "nameLength") return compactLength >= length;
    return false;
  });

  const label = mode === "nameLength"
    ? `Navn har minst ${length} bokstaver`
    : `${Object.fromEntries(nameModes)[mode]} ${letter}`;

  return {
    ok: true,
    label,
    players: setFromArray(players),
    count: players.length,
  };
}

function missingRule(message) {
  return {
    ok: false,
    label: message,
    players: new Set(),
    count: 0,
  };
}

function evaluateEditor(slotId) {
  const editor = state.editors[slotId];
  const kind = editor.kind.value;

  let result;
  if (kind === "fixed") result = evaluateFixed(editor);
  if (kind === "metric") result = evaluateMetric(editor);
  if (kind === "date") result = evaluateDate(editor);
  if (kind === "age") result = evaluateAge(editor);
  if (kind === "setCount") result = evaluateSetCount(editor);
  if (kind === "name") result = evaluateName(editor);

  editor.preview.innerHTML = result.ok
    ? `<strong>${result.count}</strong> spillere: ${escapeHtml(result.label)}`
    : escapeHtml(result.label);

  return result;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function intersectSets(a, b) {
  if (!a || !b) return new Set();
  const small = a.size <= b.size ? a : b;
  const large = a.size <= b.size ? b : a;
  return new Set([...small].filter((item) => large.has(item)));
}

function renderBoard() {
  if (!state.criteriaIndex || !state.playerFacts) return;

  const rows = [0, 1, 2].map((index) => evaluateEditor(`row-${index}`));
  const cols = [0, 1, 2].map((index) => evaluateEditor(`col-${index}`));
  const minimum = Math.max(1, Number($("#minimumCount").value || 1));
  const maximum = Math.max(minimum, Number($("#maximumCount").value || 20));
  const table = $("#sudokuGrid");
  table.innerHTML = "";

  const headerRow = document.createElement("tr");
  const corner = el("th", "corner-cell");
  corner.innerHTML = "<span class=\"axis-label\">Rader × kolonner</span><span class=\"axis-title\">Mulige spillere</span>";
  headerRow.append(corner);

  for (const [index, rule] of cols.entries()) {
    const th = document.createElement("th");
    th.innerHTML = `<span class="axis-label">Kolonne ${index + 1}</span><span class="axis-title">${escapeHtml(rule.label)}</span>`;
    headerRow.append(th);
  }
  table.append(headerRow);

  const counts = [];

  for (const [rowIndex, rowRule] of rows.entries()) {
    const tr = document.createElement("tr");
    const th = document.createElement("th");
    th.innerHTML = `<span class="axis-label">Rad ${rowIndex + 1}</span><span class="axis-title">${escapeHtml(rowRule.label)}</span>`;
    tr.append(th);

    for (const [colIndex, colRule] of cols.entries()) {
      const td = el("td", "grid-cell");
      const ready = rowRule.ok && colRule.ok;
      const players = ready ? intersectSets(rowRule.players, colRule.players) : new Set();
      const playerIds = [...players].sort(playerSort);
      const count = playerIds.length;

      if (ready) counts.push(count);

      td.classList.add(
        !ready
          ? "cell-missing"
          : count === 0
            ? "cell-empty"
            : count < minimum
              ? "cell-thin"
              : count > maximum
                ? "cell-wide"
                : "cell-good"
      );
      td.dataset.row = String(rowIndex);
      td.dataset.column = String(colIndex);

      if (!ready) {
        td.textContent = "Velg begge kriterier";
      } else {
        td.append(renderCellContent(count, playerIds));
        td.addEventListener("click", () => {
          state.selectedCell = {
            rowLabel: rowRule.label,
            columnLabel: colRule.label,
            playerIds,
          };
          renderCellDetails();
        });
      }

      tr.append(td);
    }

    table.append(tr);
  }

  const weakCells = counts.filter((count) => count < minimum).length;
  const zeroCells = counts.filter((count) => count === 0).length;
  const wideCells = counts.filter((count) => count > maximum).length;
  const minCount = counts.length ? Math.min(...counts) : 0;
  const summary = counts.length === 9
    ? `Laveste celle: ${minCount}. Under valgt minimum: ${weakCells}. Over valgt maksimum: ${wideCells}. Tomme celler: ${zeroCells}.`
    : "Velg tre radkriterier og tre kolonnekriterier.";
  $("#boardSummary").textContent = state.randomBoardNotice
    ? `${summary} ${state.randomBoardNotice}`
    : summary;
}

function renderCellContent(count, playerIds) {
  const fragment = document.createDocumentFragment();
  const countLine = el("div", "cell-count");
  countLine.innerHTML = `<strong>${count}</strong><span>mulige</span>`;
  fragment.append(countLine);

  const examples = el("ul", "examples");
  for (const playerId of playerIds.slice(0, 6)) {
    examples.append(el("li", "", playerName(playerId)));
  }
  if (playerIds.length > 6) {
    examples.append(el("li", "", `+${playerIds.length - 6} flere`));
  }
  fragment.append(examples);

  return fragment;
}

function renderCellDetails() {
  const target = $("#cellDetails");
  if (!state.selectedCell) {
    target.className = "empty-state";
    target.textContent = "Klikk på en celle for å se mulige svar.";
    return;
  }

  const { rowLabel, columnLabel, playerIds } = state.selectedCell;
  target.className = "";
  target.innerHTML = `
    <p><strong>${escapeHtml(rowLabel)}</strong> + <strong>${escapeHtml(columnLabel)}</strong></p>
    <p>${playerIds.length} mulige spillere.</p>
  `;

  const list = el("ul", "details-list");
  for (const playerId of playerIds) {
    list.append(el("li", "", playerName(playerId)));
  }
  target.append(list);
}

function renderCoverageSummary() {
  const target = $("#coverageSummary");
  target.innerHTML = "";

  for (const [status, title, body] of wishlistCoverage) {
    const item = el("div", "coverage-item");
    const tag = el("span", `coverage-tag ${status}`, status === "ok" ? "Klar" : status === "partial" ? "Delvis" : "Mangler");
    const text = el("div");
    text.innerHTML = `<strong>${escapeHtml(title)}</strong><br>${escapeHtml(body)}`;
    item.append(tag, text);
    target.append(item);
  }
}

function copyBoard() {
  const rows = [0, 1, 2].map((index) => evaluateEditor(`row-${index}`).label);
  const columns = [0, 1, 2].map((index) => evaluateEditor(`col-${index}`).label);
  const payload = JSON.stringify({
    title: "Brann-Sudoku",
    dataset: DATASETS[state.datasetMode]?.label || state.datasetMode,
    minimumCellCount: Math.max(1, Number($("#minimumCount").value || 1)),
    maximumCellCount: Math.max(1, Number($("#maximumCount").value || 20)),
    rows,
    columns,
  }, null, 2);

  navigator.clipboard?.writeText(payload);
}

function clearBoard() {
  for (const editor of Object.values(state.editors)) {
    editor.kind.value = "fixed";
    editor.lock.checked = false;
    editor.wrapper.classList.remove("is-locked");
    renderEditorControls(editor.slot.id);
  }
  state.selectedCell = null;
  state.randomBoardNotice = null;
  renderCellDetails();
  renderBoard();
}

function lockedRules() {
  const result = {};

  for (const editor of Object.values(state.editors)) {
    if (!editor.lock.checked) continue;

    const rule = evaluateEditor(editor.slot.id);
    if (!rule.ok) {
      return {
        ok: false,
        message: `${editor.slot.label} er låst, men mangler gyldig kriterium.`,
        rules: {},
      };
    }

    result[editor.slot.id] = rule;
  }

  return {
    ok: true,
    rules: result,
  };
}

function generateRandomBoard() {
  if (!state.criteriaIndex || !state.playerFacts) return;

  const requestedMinimum = Math.max(1, Number($("#minimumCount").value || 1));
  const requestedMaximum = Math.max(
    requestedMinimum,
    Number($("#maximumCount").value || 20)
  );
  const locked = lockedRules();

  if (!locked.ok) {
    state.randomBoardNotice = locked.message;
    renderBoard();
    return;
  }

  let board = findRandomBoard(
    requestedMinimum,
    requestedMaximum,
    locked.rules
  );
  let usedMinimum = requestedMinimum;

  if (!board && requestedMinimum > 1) {
    board = findRandomBoard(
      1,
      requestedMaximum,
      locked.rules
    );
    usedMinimum = 1;
  }

  if (!board) {
    state.randomBoardNotice = "Fant ikke et tilfeldig brett som passer med låser og maksgrense.";
    renderBoard();
    return;
  }

  for (const slot of editorSlots) {
    if (state.editors[slot.id].lock.checked) continue;

    const criterion = board.assignments[slot.id]?.criterion;
    if (criterion) setEditorFixedCriterion(slot.id, criterion);
  }

  state.selectedCell = null;
  state.randomBoardNotice = usedMinimum === requestedMinimum
    ? `Tilfeldig brett generert med ${requestedMinimum}-${requestedMaximum} mulige svar per celle.`
    : `Tilfeldig brett generert med 1-${requestedMaximum} mulige svar per celle.`;
  renderCellDetails();
  renderBoard();
}

async function loadData(mode = state.datasetMode) {
  try {
    const dataset = DATASETS[mode] || DATASETS.all;
    state.datasetMode = mode;
    $("#datasetMode").value = mode;
    $("#dataStatus").textContent = `Laster ${dataset.label}...`;

    const [criteriaIndex, playerFacts] = await Promise.all([
      fetch(dataset.criteriaUrl).then((response) => {
        if (!response.ok) {
          throw new Error(`${dataset.criteriaUrl}: ${response.status}`);
        }
        return response.json();
      }),
      fetch(dataset.factsUrl).then((response) => {
        if (!response.ok) {
          throw new Error(`${dataset.factsUrl}: ${response.status}`);
        }
        return response.json();
      }),
    ]);

    state.criteriaIndex = criteriaIndex;
    state.playerFacts = playerFacts;

    state.selectedCell = null;
    state.randomBoardNotice = null;
    $("#dataStatus").textContent = `${dataset.label}: ${criteriaIndex.playerCount} spillere, ${criteriaIndex.criteriaCount} ferdige kriterier, ${criteriaIndex.metricFamilyCount} metric-familier.`;
    populateDatalists();
    initializeEditors();
    renderCoverageSummary();
    renderCellDetails();
    renderBoard();
  } catch (error) {
    $("#dataStatus").textContent = "Kunne ikke laste data.";
    $(".workspace").innerHTML = `
      <div class="error-box">
        <h2>Data ble ikke lastet</h2>
        <p>${escapeHtml(error.message)}</p>
        <p>Kjør siden via en lokal webserver fra repoet, for eksempel <code>python -m http.server 8001 --directory docs</code>.</p>
      </div>
    `;
  }
}

function initializeEditors() {
  $("#rowEditors").innerHTML = "";
  $("#columnEditors").innerHTML = "";

  for (const slot of editorSlots) {
    const editor = createEditor(slot);
    const target = slot.axis === "row" ? $("#rowEditors") : $("#columnEditors");
    target.append(editor);
  }
}

$("#minimumCount").addEventListener("input", () => {
  state.randomBoardNotice = null;
  renderBoard();
});
$("#maximumCount").addEventListener("input", () => {
  state.randomBoardNotice = null;
  renderBoard();
});
$("#datasetMode").addEventListener("change", (event) => {
  loadData(event.target.value);
});
$("#clearBoard").addEventListener("click", clearBoard);
$("#copyBoard").addEventListener("click", copyBoard);
$("#generateRandomBoard").addEventListener("click", generateRandomBoard);

loadData();
