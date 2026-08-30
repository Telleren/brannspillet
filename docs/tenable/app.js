const DATA_URL = "./questions.json";

let data = null;
let currentQuestion = null;
let guessedIds = [];
let mistakes = 0;
let revealed = false;
let selectedAnswer = null;

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
const answerButton = document.querySelector("#answer-button");
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
  return [player.name, player.fullName, ...(player.aliases || [])]
    .filter(Boolean)
    .map(normalizeText);
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
  if (!metric) {
    return String(value);
  }

  return `${value} ${metric}`;
}

function setSelectedAnswer(answer) {
  selectedAnswer = answer;
  answerButton.disabled = !selectedAnswer;
  answerInput.classList.toggle("is-selected", Boolean(selectedAnswer));
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

function suggestionPool() {
  if (!currentQuestion) {
    return [];
  }

  if (currentQuestion.suggestionPool === "answers") {
    return currentQuestion.eligibleAnswers;
  }

  if (currentQuestion.suggestionPool === "custom") {
    return currentQuestion.suggestionOptions || currentQuestion.eligibleAnswers;
  }

  return (
    (data.playerPools && data.playerPools[currentQuestion.playerPoolId]) ||
    currentQuestion.eligibleAnswers
  );
}

function suggestionSubtitle(option) {
  const details = [];

  if (option.fullName && option.fullName !== option.name) {
    details.push(option.fullName);
  }

  if (option.aliases && option.aliases.length) {
    details.push(option.aliases.join(", "));
  }

  return details.join(" · ");
}

function matchingSuggestions(query) {
  const wanted = normalizeText(query);

  if (wanted.length < 2) {
    return [];
  }

  return suggestionPool()
    .filter(
      (option) =>
        !guessedIds.includes(option.id) &&
        namesFor(option).join(" ").includes(wanted)
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
}

function renderSuggestions() {
  playerSuggestions.replaceChildren();

  if (!currentQuestion) {
    return;
  }

  const options = matchingSuggestions(answerInput.value);

  for (const option of options) {
    const button = document.createElement("button");
    const subtitle = suggestionSubtitle(option);
    const name = document.createElement("strong");
    button.className = "suggestion";
    button.type = "button";
    name.textContent = option.name;
    button.append(name);

    if (subtitle) {
      const details = document.createElement("span");
      details.textContent = subtitle;
      button.append(details);
    }

    button.addEventListener("click", () => {
      setSelectedAnswer(option);
      answerInput.value = option.name;
      playerSuggestions.replaceChildren();
      answerInput.focus();
    });
    playerSuggestions.append(button);
  }
}

function matchSelectedAnswer() {
  if (!selectedAnswer) {
    return { status: "empty" };
  }

  if (guessedIds.includes(selectedAnswer.id)) {
    return { status: "duplicate", player: selectedAnswer };
  }

  const match = currentQuestion.eligibleAnswers.find(
    (answer) => answer.id === selectedAnswer.id
  );

  if (!match) {
    return { status: "wrong", player: selectedAnswer };
  }

  return { status: "correct", player: match };
}

function startGame(event) {
  event.preventDefault();

  currentQuestion = chooseOne(data.questions);
  guessedIds = [];
  mistakes = 0;
  revealed = false;
  setSelectedAnswer(null);

  periodLabel.textContent =
    currentQuestion.yearLabel ||
    `${currentQuestion.startYear}-${currentQuestion.endYear}`;
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
  renderSuggestions();

  menuView.classList.add("hidden");
  gameView.classList.remove("hidden");
  answerInput.focus();
}

function submitAnswer(event) {
  event.preventDefault();

  if (!currentQuestion || answerInput.disabled) {
    return;
  }

  const result = matchSelectedAnswer();
  answerInput.value = "";
  setSelectedAnswer(null);
  renderSuggestions();

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
  setSelectedAnswer(null);
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

  modeMeta.textContent = `${data.questions.length} mulige oppgaver`;
}

async function init() {
  const response = await fetch(DATA_URL);
  data = await response.json();
  updateModeMeta();
}

modeForm.addEventListener("submit", startGame);
answerForm.addEventListener("submit", submitAnswer);
answerInput.addEventListener("input", () => {
  setSelectedAnswer(null);
  renderSuggestions();
});
answerInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || selectedAnswer) {
    return;
  }

  const first = matchingSuggestions(answerInput.value)[0];

  if (!first) {
    return;
  }

  event.preventDefault();
  setSelectedAnswer(first);
  answerInput.value = first.name;
  playerSuggestions.replaceChildren();
});
revealButton.addEventListener("click", revealAnswers);
menuButton.addEventListener("click", showMenu);
backButton.addEventListener("click", showMenu);

init().catch(() => {
  modeMeta.textContent = "Kunne ikke laste oppgaver";
});
