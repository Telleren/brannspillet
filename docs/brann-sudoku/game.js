const DEFAULT_START_YEAR = 2000;
const MIN_START_YEAR = 1990;
const MAX_START_YEAR = 2010;
const END_YEAR = 2026;
const MAX_CELL_SCORE = 1000;

const state = {
  criteriaIndex: null,
  playerFacts: null,
  loadedStartYear: null,
  dataCache: new Map(),
  players: [],
  board: null,
  wrongGuesses: new Map(),
  roundOver: false,
};

const slotIds = [
  "row-0",
  "row-1",
  "row-2",
  "col-0",
  "col-1",
  "col-2",
];
const categoryDiversityProfiles = [
  {
    maxPerAxis: 1,
    maxTotal: 1,
    attempts: 1000,
  },
  {
    maxPerAxis: 1,
    maxTotal: 2,
    attempts: 2000,
  },
  {
    maxPerAxis: 2,
    maxTotal: 2,
    attempts: 1500,
  },
  {
    maxPerAxis: 3,
    maxTotal: 6,
    attempts: 1500,
  },
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

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function playerName(playerId) {
  return state.playerFacts.players[playerId]?.name || playerId;
}

function playerAppearances(playerId) {
  return Number(
    state.playerFacts.players[playerId]?.stats?.appearances || 0
  );
}

function playerSort(a, b) {
  const playerA = state.playerFacts.players[a];
  const playerB = state.playerFacts.players[b];
  return (playerA?.searchText || playerA?.name || a)
    .localeCompare(playerB?.searchText || playerB?.name || b, "nb")
    || a.localeCompare(b);
}

function countSort(a, b) {
  return playerAppearances(a) - playerAppearances(b) || playerSort(a, b);
}

function setFromArray(values) {
  return new Set(values || []);
}

function criterionPlayerSet(criterion) {
  return setFromArray(criterion.players);
}

function intersectSets(a, b) {
  const small = a.size <= b.size ? a : b;
  const large = a.size <= b.size ? b : a;
  const result = new Set();

  for (const item of small) {
    if (large.has(item)) result.add(item);
  }

  return result;
}

function intersectionCount(a, b) {
  let count = 0;
  const small = a.size <= b.size ? a : b;
  const large = a.size <= b.size ? b : a;

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
      const row = assignments[`row-${rowIndex}`];
      const column = assignments[`col-${colIndex}`];

      if (row && column) {
        result.push(intersectSets(row.players, column.players));
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

function ruleFromCriterion(criterion) {
  return {
    id: criterion.id,
    label: criterion.label,
    players: criterionPlayerSet(criterion),
    count: criterion.count,
    category: criterion.category || "unknown",
    criterion,
  };
}

function axisForSlotId(slotId) {
  return slotId.startsWith("row") ? "row" : "col";
}

function categoryForRule(rule) {
  return rule?.category || rule?.criterion?.category || "unknown";
}

function oppositeSlotIds(slotId) {
  const prefix = slotId.startsWith("row") ? "col" : "row";
  return [0, 1, 2].map((index) => `${prefix}-${index}`);
}

function ruleFitsSlot(
  slotId,
  rule,
  assignments,
  minimum,
  maximum,
  allowOverlappingAnswers
) {
  const fitsCounts = oppositeSlotIds(slotId).every((oppositeSlotId) => {
    const opposite = assignments[oppositeSlotId];
    if (!opposite) return true;
    return intersectionFitsRange(
      rule.players,
      opposite.players,
      minimum,
      maximum
    );
  });

  if (!fitsCounts) return false;

  if (allowOverlappingAnswers) return true;

  return cellPlayerSetsAreDisjoint({
    ...assignments,
    [slotId]: rule,
  });
}

function ruleFitsCategoryProfile(slotId, rule, assignments, profile) {
  const counts = categoryCountsForSlot(slotId, rule, assignments);

  return (
    counts.total < profile.maxTotal
    && counts.axis < profile.maxPerAxis
  );
}

function categoryCountsForSlot(slotId, rule, assignments) {
  const category = categoryForRule(rule);
  const axis = axisForSlotId(slotId);
  let totalCount = 0;
  let axisCount = 0;

  for (const [assignedSlotId, assignedRule] of Object.entries(assignments)) {
    if (categoryForRule(assignedRule) !== category) {
      continue;
    }

    totalCount += 1;

    if (axisForSlotId(assignedSlotId) === axis) {
      axisCount += 1;
    }
  }

  return {
    total: totalCount,
    axis: axisCount,
  };
}

function categoryPressure(slotId, rule, assignments) {
  const counts = categoryCountsForSlot(slotId, rule, assignments);
  return (counts.axis * 10) + counts.total;
}

function validateAssignments(
  assignments,
  minimum,
  maximum,
  allowOverlappingAnswers
) {
  for (let rowIndex = 0; rowIndex < 3; rowIndex += 1) {
    for (let colIndex = 0; colIndex < 3; colIndex += 1) {
      const row = assignments[`row-${rowIndex}`];
      const column = assignments[`col-${colIndex}`];
      if (!row || !column) continue;
      if (!intersectionFitsRange(row.players, column.players, minimum, maximum)) {
        return false;
      }
    }
  }

  return (
    allowOverlappingAnswers
    || cellPlayerSetsAreDisjoint(assignments)
  );
}

function firstMatchingRule(
  candidates,
  used,
  slotId,
  assignments,
  profile,
  minimum,
  maximum,
  allowOverlappingAnswers
) {
  let bestRule = null;
  let bestPressure = Infinity;

  for (const criterion of shuffle(candidates)) {
    if (used.has(criterion.id)) {
      continue;
    }

    const rule = ruleFromCriterion(criterion);

    if (!ruleFitsCategoryProfile(slotId, rule, assignments, profile)) {
      continue;
    }

    if (!ruleFitsSlot(
      slotId,
      rule,
      assignments,
      minimum,
      maximum,
      allowOverlappingAnswers
    )) {
      continue;
    }

    const pressure = categoryPressure(slotId, rule, assignments);

    if (pressure < bestPressure) {
      bestRule = rule;
      bestPressure = pressure;

      if (pressure === 0) {
        return bestRule;
      }
    }
  }

  return bestRule;
}

function randomizableCriteria(minimum) {
  return Object.values(state.criteriaIndex.criteria)
    .filter((criterion) => (
      criterion.id !== "player:any"
      && Array.isArray(criterion.players)
      && criterion.players.length >= minimum
      && criterion.players.length < state.criteriaIndex.playerCount
    ));
}

function findRandomBoard(minimum, maximum, allowOverlappingAnswers) {
  const candidates = randomizableCriteria(minimum);

  for (const profile of categoryDiversityProfiles) {
    for (let attempt = 0; attempt < profile.attempts; attempt += 1) {
      const assignments = {};
      const used = new Set();
      let failed = false;

      for (const slotId of slotIds) {
        const rule = firstMatchingRule(
          candidates,
          used,
          slotId,
          assignments,
          profile,
          minimum,
          maximum,
          allowOverlappingAnswers
        );

        if (!rule) {
          failed = true;
          break;
        }

        assignments[slotId] = rule;
        used.add(rule.id);
      }

      if (
        !failed
        && validateAssignments(
          assignments,
          minimum,
          maximum,
          allowOverlappingAnswers
        )
      ) {
        return assignments;
      }
    }
  }

  return null;
}

function bestPlayerForCell(playerIds) {
  return [...playerIds].sort(countSort)[0] || null;
}

function scoreForCell(cell, playerId) {
  if (!cell || !playerId) return 0;

  const appearanceCounts = cell.playerIds.map(playerAppearances);
  const minimum = Math.min(...appearanceCounts);
  const maximum = Math.max(...appearanceCounts);
  const playerValue = playerAppearances(playerId);

  if (playerValue === minimum || maximum === minimum) return MAX_CELL_SCORE;

  return Math.max(
    1,
    Math.round(
      MAX_CELL_SCORE * ((maximum - playerValue + 1) / (maximum - minimum + 1))
    )
  );
}

function buildBoard(assignments, minimum, maximum) {
  const rows = [0, 1, 2].map((index) => assignments[`row-${index}`]);
  const columns = [0, 1, 2].map((index) => assignments[`col-${index}`]);
  const cells = [];

  for (let rowIndex = 0; rowIndex < 3; rowIndex += 1) {
    const row = [];

    for (let colIndex = 0; colIndex < 3; colIndex += 1) {
      const playerSet = intersectSets(
        rows[rowIndex].players,
        columns[colIndex].players
      );
      const playerIds = [...playerSet].sort(countSort);
      row.push({
        rowIndex,
        colIndex,
        playerIds,
        filledBy: null,
        bestPlayerId: bestPlayerForCell(playerIds),
      });
    }

    cells.push(row);
  }

  return {
    rows,
    columns,
    cells,
    minimum,
    maximum,
  };
}

function allCells() {
  return state.board?.cells.flat() || [];
}

function filledCells() {
  return allCells().filter((cell) => cell.filledBy);
}

function currentScore() {
  return filledCells()
    .reduce((sum, cell) => sum + scoreForCell(cell, cell.filledBy), 0);
}

function maximumScore() {
  return allCells().length * MAX_CELL_SCORE;
}

function boardIsComplete() {
  return allCells().every((cell) => cell.filledBy);
}

function renderStartStatus(message) {
  $("#dataStatus").textContent = message;
}

function showGame() {
  $("#startScreen").hidden = true;
  $("#gameScreen").hidden = false;
}

function showStart() {
  $("#gameScreen").hidden = true;
  $("#startScreen").hidden = false;
}

function clampStartYear(value) {
  return Math.min(
    MAX_START_YEAR,
    Math.max(
      MIN_START_YEAR,
      Number(value || DEFAULT_START_YEAR)
    )
  );
}

function selectedStartYear() {
  return clampStartYear($("#startYear").value);
}

function criteriaUrlForStartYear(startYear) {
  return `../shared/grid-ranges/grid-criteria-index-since-${startYear}.json`;
}

function factsUrlForStartYear(startYear) {
  return `../shared/grid-ranges/player-facts-since-${startYear}.json`;
}

function updateStartYearDisplay() {
  const startYear = selectedStartYear();
  $("#startYear").value = String(startYear);
  $("#startYearValue").textContent = String(startYear);

  if (state.loadedStartYear === startYear && state.players.length) {
    renderStartStatus(
      `${state.players.length} Brann-spillere fra ${startYear} til ${END_YEAR} klare.`
    );
  } else if (state.loadedStartYear !== null) {
    renderStartStatus(
      `Klar til å laste Brann-data fra ${startYear} til ${END_YEAR}.`
    );
  }
}

function setFeedback(message, kind = "") {
  const feedback = $("#feedback");
  feedback.textContent = message;
  feedback.className = kind ? `feedback ${kind}` : "feedback";
}

function renderScore() {
  $("#scoreValue").textContent = `${currentScore()} / ${maximumScore()}`;
}

function renderBoard() {
  const table = $("#sudokuGrid");
  table.innerHTML = "";

  if (!state.board) return;

  const headerRow = document.createElement("tr");
  headerRow.append(el("th", "corner-cell", "Brann"));

  for (const criterion of state.board.columns) {
    const th = el("th", "axis-cell", criterion.label);
    headerRow.append(th);
  }

  table.append(headerRow);

  for (let rowIndex = 0; rowIndex < 3; rowIndex += 1) {
    const tr = document.createElement("tr");
    tr.append(el("th", "axis-cell", state.board.rows[rowIndex].label));

    for (let colIndex = 0; colIndex < 3; colIndex += 1) {
      tr.append(renderCell(state.board.cells[rowIndex][colIndex]));
    }

    table.append(tr);
  }

  renderScore();
}

function renderCell(cell) {
  const td = el("td", "grid-cell");
  const count = cell.playerIds.length;

  if (cell.filledBy) {
    const score = scoreForCell(cell, cell.filledBy);
    td.classList.add(score === MAX_CELL_SCORE ? "is-perfect" : "is-filled");
    td.innerHTML = `
      <strong>${escapeHtml(playerName(cell.filledBy))}</strong>
      <span>${playerAppearances(cell.filledBy)} kamper</span>
      <em>${score} poeng</em>
    `;
    return td;
  }

  if (state.roundOver) {
    const bestPlayerId = cell.bestPlayerId;
    td.classList.add("is-revealed");
    td.innerHTML = bestPlayerId
      ? `
        <small>Beste svar</small>
        <strong>${escapeHtml(playerName(bestPlayerId))}</strong>
        <span>${playerAppearances(bestPlayerId)} kamper</span>
      `
      : "<small>Ingen svar</small>";
    return td;
  }

  td.innerHTML = `
    <strong></strong>
    <span>${count} mulige</span>
  `;
  return td;
}

function renderWrongGuesses() {
  const list = $("#wrongGuesses");
  list.innerHTML = "";

  for (const player of state.wrongGuesses.values()) {
    list.append(el("li", "", player.name));
  }

  if (!state.wrongGuesses.size) {
    list.append(el("li", "muted", "Ingen ennå"));
  }
}

function renderSummary() {
  const summary = $("#roundSummary");
  const filled = filledCells().length;
  const total = allCells().length;

  if (!state.board) {
    summary.textContent = "";
    return;
  }

  if (state.roundOver) {
    summary.textContent = `${filled}/${total} celler fylt. Sluttscore: ${currentScore()} / ${maximumScore()}.`;
  } else {
    summary.textContent = `${filled}/${total} celler fylt.`;
  }
}

function renderRound() {
  renderBoard();
  renderWrongGuesses();
  renderSummary();
  $("#giveUpButton").textContent = state.roundOver
    ? "Generer nytt brett"
    : "Gi opp";
}

function matchingSearchPlayers(query) {
  const normalized = normalizeText(query);
  if (normalized.length < 2) return [];

  return state.players
    .filter((player) => player.searchText.includes(normalized))
    .slice(0, 12);
}

function renderSuggestions() {
  const target = $("#suggestions");
  const query = $("#playerSearch").value;
  const matches = state.roundOver ? [] : matchingSearchPlayers(query);
  target.innerHTML = "";

  for (const player of matches) {
    const button = el("button", "suggestion", "");
    button.type = "button";
    button.append(el("strong", "", player.name));
    button.addEventListener("click", () => handleGuess(player.id));
    target.append(button);
  }
}

function handleGuess(playerId) {
  if (!state.board || state.roundOver) return;

  const player = state.playerFacts.players[playerId];
  const matchingCells = allCells()
    .filter((cell) => (
      !cell.filledBy
      && cell.playerIds.includes(playerId)
    ));

  $("#playerSearch").value = "";
  $("#suggestions").innerHTML = "";

  if (!matchingCells.length) {
    if (!state.wrongGuesses.has(playerId)) {
      state.wrongGuesses.set(playerId, {
        id: playerId,
        name: player?.name || playerId,
      });
    }
    setFeedback(`${player?.name || playerId} er ikke et riktig svar i noen åpne celler.`, "bad");
    renderRound();
    return;
  }

  for (const cell of matchingCells) {
    cell.filledBy = playerId;
  }

  const cellText = matchingCells.length === 1 ? "celle" : "celler";
  setFeedback(`${player.name} fyller ${matchingCells.length} ${cellText}.`, "good");

  if (boardIsComplete()) {
    finishRound("Brettet er fylt!");
  } else {
    renderRound();
  }
}

function finishRound(message = "Runden er avsluttet.") {
  state.roundOver = true;
  $("#playerSearch").disabled = true;
  $("#suggestions").innerHTML = "";
  setFeedback(`${message} Score: ${currentScore()} / ${maximumScore()}.`, "good");
  renderRound();
}

async function startRound() {
  const startYear = selectedStartYear();

  $("#generateBoard").disabled = true;
  await loadData(startYear);

  if (!state.criteriaIndex || !state.playerFacts) {
    $("#generateBoard").disabled = false;
    return;
  }

  const minimum = Math.max(1, Number($("#minimumCount").value || 2));
  const maximum = Math.max(minimum, Number($("#maximumCount").value || 6));
  const allowOverlappingAnswers = $("#allowOverlappingAnswers").checked;
  $("#minimumCount").value = String(minimum);
  $("#maximumCount").value = String(maximum);
  renderStartStatus("Genererer brett...");

  const assignments = findRandomBoard(
    minimum,
    maximum,
    allowOverlappingAnswers
  );

  if (!assignments) {
    renderStartStatus(
      allowOverlappingAnswers
        ? `Fant ikke brett med ${minimum}-${maximum} mulige svar per celle.`
        : `Fant ikke brett med ${minimum}-${maximum} mulige svar per celle uten overlappende spillere.`
    );
    $("#generateBoard").disabled = false;
    return;
  }

  state.board = buildBoard(assignments, minimum, maximum);
  state.wrongGuesses = new Map();
  state.roundOver = false;
  $("#playerSearch").disabled = false;
  $("#playerSearch").value = "";
  setFeedback("");
  showGame();
  renderRound();
  $("#generateBoard").disabled = false;
  $("#playerSearch").focus();
}

function giveUpOrNewRound() {
  if (state.roundOver) {
    showStart();
    startRound();
    return;
  }

  finishRound("Du ga opp.");
}

function applyLoadedData(startYear, criteriaIndex, playerFacts) {
  state.criteriaIndex = criteriaIndex;
  state.playerFacts = playerFacts;
  state.loadedStartYear = startYear;
  state.players = Object.values(playerFacts.players)
    .map((player) => ({
      id: player.id,
      name: player.name,
      searchText: player.searchText,
    }))
    .sort((a, b) => (
      a.searchText.localeCompare(b.searchText, "nb")
      || a.id.localeCompare(b.id)
    ));
}

async function loadData(startYear = DEFAULT_START_YEAR) {
  const safeStartYear = clampStartYear(startYear);

  if (state.loadedStartYear === safeStartYear) {
    return;
  }

  if (state.dataCache.has(safeStartYear)) {
    const cached = state.dataCache.get(safeStartYear);
    applyLoadedData(
      safeStartYear,
      cached.criteriaIndex,
      cached.playerFacts
    );
    renderStartStatus(
      `${state.players.length} Brann-spillere fra ${safeStartYear} til ${END_YEAR} klare.`
    );
    return;
  }

  try {
    $("#generateBoard").disabled = true;
    renderStartStatus(
      `Laster Brann-data fra ${safeStartYear} til ${END_YEAR}...`
    );

    const criteriaUrl = criteriaUrlForStartYear(safeStartYear);
    const factsUrl = factsUrlForStartYear(safeStartYear);
    const [criteriaIndex, playerFacts] = await Promise.all([
      fetch(criteriaUrl).then((response) => {
        if (!response.ok) throw new Error(`${criteriaUrl}: ${response.status}`);
        return response.json();
      }),
      fetch(factsUrl).then((response) => {
        if (!response.ok) throw new Error(`${factsUrl}: ${response.status}`);
        return response.json();
      }),
    ]);

    state.dataCache.set(
      safeStartYear,
      {
        criteriaIndex,
        playerFacts,
      }
    );
    applyLoadedData(
      safeStartYear,
      criteriaIndex,
      playerFacts
    );

    renderStartStatus(
      `${state.players.length} Brann-spillere fra ${safeStartYear} til ${END_YEAR} klare.`
    );
    $("#generateBoard").disabled = false;
  } catch (error) {
    renderStartStatus(`Kunne ikke laste data: ${error.message}`);
    $("#generateBoard").disabled = true;
  }
}

$("#generateBoard").addEventListener("click", startRound);
$("#giveUpButton").addEventListener("click", giveUpOrNewRound);
$("#startYear").addEventListener("input", updateStartYearDisplay);
$("#playerSearch").addEventListener("input", renderSuggestions);
$("#playerSearch").addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  const first = matchingSearchPlayers($("#playerSearch").value)[0];
  if (first) handleGuess(first.id);
});

$("#generateBoard").disabled = true;
updateStartYearDisplay();
loadData(DEFAULT_START_YEAR);
