const DATA_URL = "./puzzles.json";
const STARTING_LIVES = 3;

let data = null;
let selectedPuzzles = [];
let playerPool = [];
let usedPuzzleIds = new Set();
let currentPuzzle = null;
let score = 0;
let mistakes = 0;

const setupView = document.querySelector("#setup-view");
const gameView = document.querySelector("#game-view");
const setupForm = document.querySelector("#setup-form");
const answerForm = document.querySelector("#answer-form");
const resultPanel = document.querySelector("#result-panel");
const yearMin = document.querySelector("#year-min");
const yearMax = document.querySelector("#year-max");
const yearOutput = document.querySelector("#year-output");
const candidateCount = document.querySelector("#candidate-count");
const rangeLabel = document.querySelector("#range-label");
const scoreValue = document.querySelector("#score-value");
const livesValue = document.querySelector("#lives-value");
const matchDate = document.querySelector("#match-date");
const matchTitle = document.querySelector("#match-title");
const matchScore = document.querySelector("#match-score");
const lineup = document.querySelector("#lineup");
const answerInput = document.querySelector("#answer-input");
const playerSuggestions = document.querySelector("#player-suggestions");
const feedback = document.querySelector("#feedback");
const finalScore = document.querySelector("#final-score");
const restartButton = document.querySelector("#restart-button");
const backButton = document.querySelector("#back-button");
const finalDetail = document.querySelector("#final-detail");

function normalizeText(text) {
  return (text || "")
    .toLocaleLowerCase("nb-NO")
    .trim()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");
}

function shuffle(items) {
  const copy = [...items];

  for (let index = copy.length - 1; index > 0; index -= 1) {
    const other = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[other]] = [copy[other], copy[index]];
  }

  return copy;
}

function chooseOne(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function clampYears() {
  let start = Number(yearMin.value);
  let end = Number(yearMax.value);

  if (start > end) {
    [start, end] = [end, start];
  }

  yearOutput.value = `${start}-${end}`;

  if (!data) {
    return { start, end };
  }

  const count = data.puzzles.filter(
    (puzzle) => puzzle.year >= start && puzzle.year <= end
  ).length;

  candidateCount.textContent = `${count} lagoppstillinger`;
  return { start, end };
}

function setScoreboard() {
  scoreValue.textContent = String(score);
  livesValue.textContent = String(STARTING_LIVES - mistakes);
}

function namesFor(player) {
  return [player.name, player.fullName].filter(Boolean).map(normalizeText);
}

function buildPlayerPool(puzzles) {
  const playersById = new Map();

  for (const puzzle of puzzles) {
    for (const player of puzzle.lineup) {
      if (!playersById.has(player.id)) {
        playersById.set(player.id, {
          id: player.id,
          name: player.name,
          fullName: player.fullName,
          search: namesFor(player).join(" "),
        });
      }
    }
  }

  return [...playersById.values()].sort((a, b) =>
    a.name.localeCompare(b.name, "nb-NO")
  );
}

function updateSuggestions() {
  playerSuggestions.replaceChildren();

  if (!currentPuzzle) {
    return;
  }

  const wanted = normalizeText(answerInput.value);

  if (wanted.length < 2) {
    return;
  }

  const visiblePlayerIds = new Set(
    currentPuzzle.lineup
      .filter((player) => !player.hidden)
      .map((player) => player.id)
  );

  const options = playerPool
    .filter(
      (player) =>
        !visiblePlayerIds.has(player.id) &&
        player.search.includes(wanted)
    )
    .sort((a, b) => {
      const aStarts = normalizeText(a.name).startsWith(wanted) ? 0 : 1;
      const bStarts = normalizeText(b.name).startsWith(wanted) ? 0 : 1;

      if (aStarts !== bStarts) {
        return aStarts - bStarts;
      }

      return a.name.localeCompare(b.name, "nb-NO");
    })
    .slice(0, 12);

  for (const player of options) {
    const option = document.createElement("option");
    option.value = player.name;
    playerSuggestions.append(option);
  }
}

function isCorrectAnswer(answer, puzzle) {
  const wanted = normalizeText(answer);

  if (!wanted) {
    return false;
  }

  const hiddenNames = puzzle.answer.names.map(normalizeText);

  if (hiddenNames.includes(wanted)) {
    return true;
  }

  if (wanted.length < 3) {
    return false;
  }

  const matches = puzzle.lineup
    .filter((player) => namesFor(player).some((name) => name.includes(wanted)))
    .map((player) => player.id);

  return (
    new Set(matches).size === 1 &&
    matches[0] === puzzle.answer.id
  );
}

function clearFeedback() {
  feedback.textContent = "";
  feedback.className = "feedback";
}

function showFeedback(text, kind) {
  feedback.textContent = text;
  feedback.className = `feedback ${kind}`;
}

function renderLineup(puzzle) {
  lineup.replaceChildren();

  for (const groupName of data.groupOrder) {
    const players = puzzle.lineup.filter((player) => player.role === groupName);

    if (players.length === 0) {
      continue;
    }

    const group = document.createElement("section");
    group.className = "lineup-group";

    const title = document.createElement("div");
    title.className = "group-title";
    title.textContent = groupName;
    group.append(title);

    const playerGrid = document.createElement("div");
    playerGrid.className = "players";

    for (const player of players) {
      const row = document.createElement("div");
      row.className = player.hidden ? "player-row missing-row" : "player-row";

      const shirt = document.createElement("span");
      shirt.className = "shirt";
      shirt.textContent = player.hidden ? "--" : player.shirt;

      const name = document.createElement("span");
      name.textContent = player.hidden ? "--- MANGLER ---" : player.name;

      row.append(shirt, name);
      playerGrid.append(row);
    }

    group.append(playerGrid);
    lineup.append(group);
  }
}

function renderPuzzle(puzzle) {
  const answer = chooseOne(puzzle.hiddenCandidates);

  currentPuzzle = {
    ...puzzle,
    answer,
    lineup: puzzle.lineup.map((player) => ({
      ...player,
      hidden: player.id === answer.id,
    })),
  };

  matchDate.textContent = `${puzzle.date} | ${puzzle.competition}`;
  matchTitle.textContent = `${puzzle.homeTeam}-${puzzle.awayTeam}`;
  matchScore.textContent = puzzle.score;
  answerInput.value = "";
  answerInput.disabled = false;
  clearFeedback();
  setScoreboard();
  updateSuggestions();
  renderLineup(currentPuzzle);
  answerInput.focus();
}

function nextPuzzle() {
  const next = selectedPuzzles.find((puzzle) => !usedPuzzleIds.has(puzzle.id));

  if (!next) {
    endGame("Ingen flere lagoppstillinger i utvalget.");
    return;
  }

  usedPuzzleIds.add(next.id);
  renderPuzzle(next);
}

function endGame(message) {
  answerInput.disabled = true;
  answerForm.classList.add("hidden");
  resultPanel.classList.remove("hidden");
  finalScore.textContent = `${score} ${score === 1 ? "riktig" : "riktige"}`;
  finalDetail.textContent = message
    ? `${message} ${mistakes}/${STARTING_LIVES} feil.`
    : `${mistakes}/${STARTING_LIVES} feil.`;

  if (message) {
    showFeedback(message, "wrong");
  }
}

function startGame(event) {
  event.preventDefault();

  const { start, end } = clampYears();
  selectedPuzzles = shuffle(
    data.puzzles.filter(
      (puzzle) => puzzle.year >= start && puzzle.year <= end
    )
  );

  if (selectedPuzzles.length === 0) {
    candidateCount.textContent = "Ingen lagoppstillinger";
    return;
  }

  score = 0;
  mistakes = 0;
  playerPool = buildPlayerPool(selectedPuzzles);
  usedPuzzleIds = new Set();
  rangeLabel.textContent = `${start}-${end}`;
  setupView.classList.add("hidden");
  gameView.classList.remove("hidden");
  answerForm.classList.remove("hidden");
  resultPanel.classList.add("hidden");
  nextPuzzle();
}

function submitAnswer(event) {
  event.preventDefault();

  if (!currentPuzzle || answerInput.disabled) {
    return;
  }

  const correct = isCorrectAnswer(answerInput.value, currentPuzzle);
  const answer = currentPuzzle.answer.names[0];

  if (correct) {
    score += 1;
    showFeedback(`Riktig: ${answer}`, "correct");
    setTimeout(nextPuzzle, 650);
    return;
  }

  mistakes += 1;
  setScoreboard();

  if (mistakes >= STARTING_LIVES) {
    showFeedback(`Feil. Riktig svar var ${answer}.`, "wrong");
    setTimeout(() => endGame("Tredje feil. Streaken er over."), 900);
    return;
  }

  showFeedback(
    `Feil. Riktig svar var ${answer}. ${STARTING_LIVES - mistakes} liv igjen.`,
    "wrong"
  );
  setTimeout(nextPuzzle, 1100);
}

function goBackToSetup() {
  gameView.classList.add("hidden");
  setupView.classList.remove("hidden");
  currentPuzzle = null;
}

async function init() {
  const response = await fetch(DATA_URL);
  data = await response.json();

  yearMin.min = data.minYear;
  yearMin.max = data.maxYear;
  yearMin.value = data.minYear;
  yearMax.min = data.minYear;
  yearMax.max = data.maxYear;
  yearMax.value = data.maxYear;
  clampYears();
}

yearMin.addEventListener("input", clampYears);
yearMax.addEventListener("input", clampYears);
answerInput.addEventListener("input", updateSuggestions);
setupForm.addEventListener("submit", startGame);
answerForm.addEventListener("submit", submitAnswer);
restartButton.addEventListener("click", startGame);
backButton.addEventListener("click", goBackToSetup);

init().catch(() => {
  candidateCount.textContent = "Kunne ikke laste kampdata";
});
