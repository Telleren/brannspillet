const DATA_URL = "./questions.json";

let data = null;
let currentPeriod = null;
let currentQuestion = null;
let guessedIds = [];
let mistakes = 0;
let revealed = false;

const menuView = document.querySelector("#menu-view");
const gameView = document.querySelector("#game-view");
const modeForm = document.querySelector("#mode-form");
const modeMeta = document.querySelector("#mode-meta");
const periodLabel = document.querySelector("#period-label");
const questionTitle = document.querySelector("#question-title");
const questionDescription = document.querySelector("#question-description");
const scoreValue = document.querySelector("#score-value");
const livesValue = document.querySelector("#lives-value");
const board = document.querySelector("#board");
const answerForm = document.querySelector("#answer-form");
const answerInput = document.querySelector("#answer-input");
const playerSuggestions = document.querySelector("#player-suggestions");
const feedback = document.querySelector("#feedback");
const gameOver = document.querySelector("#game-over");
const gameOverLabel = document.querySelector("#game-over-label");
const finalScore = document.querySelector("#final-score");
const revealButton = document.querySelector("#reveal-button");
const menuButton = document.querySelector("#menu-button");
const backButton = document.querySelector("#back-button");

function normalizeText(text) {
  return (text || "")
    .toLocaleLowerCase("nb-NO")
    .trim()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");
}

function chooseOne(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function namesFor(player) {
  return [player.name, player.fullName].filter(Boolean).map(normalizeText);
}

function getSlotResults(includeReveal = false) {
  const usedIds = new Set();

  return currentQuestion.slots.map((slot) => {
    const playersById = new Map(
      slot.players.map((player) => [player.id, player])
    );
    let player = null;

    for (const id of guessedIds) {
      if (playersById.has(id) && !usedIds.has(id)) {
        player = playersById.get(id);
        usedIds.add(id);
        break;
      }
    }

    if (!player && includeReveal) {
      player = slot.players.find((candidate) => !usedIds.has(candidate.id));

      if (!player) {
        player = slot.players[0];
      }

      usedIds.add(player.id);
    }

    return { slot, player };
  });
}

function solvedCount() {
  return getSlotResults().filter((result) => result.player).length;
}

function setFeedback(text, kind = "") {
  feedback.textContent = text;
  feedback.className = kind ? `feedback ${kind}` : "feedback";
}

function setScoreboard() {
  scoreValue.textContent = `${solvedCount()}/${data.answerCount}`;
  livesValue.textContent = String(data.startingLives - mistakes);
}

function displayMetric(value, metric) {
  return `${value} ${metric}`;
}

function renderBoard() {
  board.replaceChildren();

  getSlotResults(revealed).forEach((result, index) => {
    const row = document.createElement("div");
    row.className = result.player || revealed ? "slot-row solved" : "slot-row";

    const number = document.createElement("span");
    number.className = "slot-index";
    number.textContent = String(index + 1);

    const name = document.createElement("span");
    name.className = "slot-name";

    if (result.player) {
      name.textContent = result.player.name;
    } else {
      name.textContent = "____________________________";
    }

    const value = document.createElement("span");
    value.className = "slot-value";
    value.textContent = displayMetric(
      result.slot.value,
      currentQuestion.metric
    );

    row.append(number, name, value);
    board.append(row);
  });
}

function updateSuggestions() {
  playerSuggestions.replaceChildren();

  if (!currentQuestion) {
    return;
  }

  const wanted = normalizeText(answerInput.value);

  if (wanted.length < 2) {
    return;
  }

  const options = currentQuestion.eligibleAnswers
    .filter(
      (player) =>
        !guessedIds.includes(player.id) &&
        namesFor(player).join(" ").includes(wanted)
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

function matchAnswer(answer) {
  const wanted = normalizeText(answer);

  if (!wanted) {
    return { status: "empty" };
  }

  let matches = [];

  for (const player of currentQuestion.eligibleAnswers) {
    const names = namesFor(player);

    if (names.includes(wanted)) {
      matches = [player];
      break;
    }

    if (wanted.length >= 3 && names.some((name) => name.includes(wanted))) {
      matches.push(player);
    }
  }

  const unique = new Map(matches.map((player) => [player.id, player]));

  if (unique.size !== 1) {
    return { status: "wrong" };
  }

  const player = [...unique.values()][0];

  if (guessedIds.includes(player.id)) {
    return { status: "duplicate", player };
  }

  return { status: "correct", player };
}

function startGame(event) {
  event.preventDefault();

  const formData = new FormData(modeForm);
  const periodId = formData.get("period");
  currentPeriod = data.periods.find((period) => period.id === periodId);
  currentQuestion = chooseOne(currentPeriod.questions);
  guessedIds = [];
  mistakes = 0;
  revealed = false;

  periodLabel.textContent = `${currentPeriod.label} (${currentPeriod.start_year}-${currentPeriod.end_year})`;
  questionTitle.textContent = currentQuestion.title;
  questionDescription.textContent = currentQuestion.description;
  answerInput.value = "";
  answerInput.disabled = false;
  answerForm.classList.remove("hidden");
  gameOver.classList.add("hidden");
  revealButton.classList.remove("hidden");
  setFeedback("");
  setScoreboard();
  renderBoard();
  updateSuggestions();

  menuView.classList.add("hidden");
  gameView.classList.remove("hidden");
  answerInput.focus();
}

function submitAnswer(event) {
  event.preventDefault();

  if (!currentQuestion || answerInput.disabled) {
    return;
  }

  const result = matchAnswer(answerInput.value);
  answerInput.value = "";
  updateSuggestions();

  if (result.status === "empty") {
    return;
  }

  if (result.status === "duplicate") {
    setFeedback(`${result.player.name} er allerede tatt.`, "wrong");
    return;
  }

  if (result.status === "correct") {
    guessedIds.push(result.player.id);
    setFeedback(`Riktig: ${result.player.name}`, "correct");
    setScoreboard();
    renderBoard();

    if (solvedCount() === data.answerCount) {
      finishGame("Full pott", false);
    }

    return;
  }

  mistakes += 1;
  setScoreboard();

  if (mistakes >= data.startingLives) {
    setFeedback("Feil. Du er tom for liv.", "wrong");
    finishGame("Spillet er over", true);
    return;
  }

  setFeedback(`Feil. ${data.startingLives - mistakes} liv igjen.`, "wrong");
}

function finishGame(label, canReveal) {
  answerInput.disabled = true;
  answerForm.classList.add("hidden");
  gameOver.classList.remove("hidden");
  gameOverLabel.textContent = label;
  finalScore.textContent = `${solvedCount()}/${data.answerCount} riktige`;

  if (canReveal) {
    revealButton.classList.remove("hidden");
  } else {
    revealButton.classList.add("hidden");
  }
}

function revealAnswers() {
  revealed = true;
  revealButton.classList.add("hidden");
  renderBoard();
}

function showMenu() {
  gameView.classList.add("hidden");
  menuView.classList.remove("hidden");
  currentQuestion = null;
}

function updateModeMeta() {
  if (!data) {
    return;
  }

  const formData = new FormData(modeForm);
  const periodId = formData.get("period");
  const period = data.periods.find((item) => item.id === periodId);
  modeMeta.textContent = `${period.questions.length} mulige oppgaver`;
}

async function init() {
  const response = await fetch(DATA_URL);
  data = await response.json();
  updateModeMeta();
}

modeForm.addEventListener("submit", startGame);
modeForm.addEventListener("change", updateModeMeta);
answerForm.addEventListener("submit", submitAnswer);
answerInput.addEventListener("input", updateSuggestions);
revealButton.addEventListener("click", revealAnswers);
menuButton.addEventListener("click", showMenu);
backButton.addEventListener("click", showMenu);

init().catch(() => {
  modeMeta.textContent = "Kunne ikke laste oppgaver";
});
