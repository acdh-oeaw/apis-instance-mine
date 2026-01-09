function filterPips(value, type) {
  if (Number.isInteger(value / 50)) {
    return 1;
  }
  if (Number.isInteger(value / 10)) {
    return 0;
  }
  return -1;
}

function initDateSlider(id, min, max, tmplt) {
  const slider = document.getElementById(id);

  noUiSlider.create(slider, {
    start: [min, max],
    connect: true,
    range: {
      min: parseInt(min),
      max: parseInt(max),
    },
    step: 1,
    pips: {
      mode: "steps",
      density: 2,
      filter: filterPips,
      format: wNumb({
        decimals: 0,
      }),
    },
    tooltips: [wNumb({ decimals: 0 }), wNumb({ decimals: 0 })],
  });
  slider.noUiSlider.on("change", updateYearAfterMove);

  const els = document.querySelectorAll("#" + id + " .noUi-tooltip");
  for (let i = 0; i < els.length; i++) {
    console.log(els.item(i));
    els.item(i).addEventListener("dblclick", toggleIncludeExclude);
  }
}
function toggleIncludeExclude(event) {
  console.log("doubleclick");
  console.log(event);
  const sel = event.target.closest(".date-slider-wrapper");
  const parent_div = event.target.parentElement;
  const kind = parent_div.classList.contains("noUi-handle-lower")
    ? "lower"
    : "upper";
  console.log(kind);
  const span_node = sel.querySelector("span#" + kind + "-bound");
  const val = parseInt(parent_div.ariaValueNow);
  console.log("numb ", val);
  console.log(sel);
  let templ;
  if (event.target.classList.contains("exclusive")) {
    templ = sel.querySelector("template#slider-" + kind + "-not-selected");
    event.target.classList.remove("exclusive");
  } else {
    templ = sel.querySelector("template#slider-" + kind + "-selected");
    event.target.classList.add("exclusive");
  }
  console.log(templ, templ.content);
  const clone = document.importNode(templ.content, true);
  span_node.replaceChildren(clone);
  const span_1 = sel.querySelector("span#" + kind + "-year");
  console.log("span1", span_1);
  span_1.textContent = val;
}
function startDateSliders(e) {
  console.log("script started");
  const els = document.getElementsByClassName("mine-date-slider");
  for (let i = 0; i < els.length; i++) {
    console.log(els.item(i));
    const item = els.item(i);
    initDateSlider(item.id, item.dataset.min, item.dataset.max);
  }
}
function updateYearAfterMove(
  values,
  handle,
  unencoded,
  tap,
  positions,
  noUiSlider,
) {
  console.log(values, handle, tap, noUiSlider.target);
  if (handle === 0) {
    noUiSlider.target.parentElement.querySelector(
      "span#lower-year",
    ).textContent = wNumb({ decimals: 0 }).to(parseFloat(values[0]));
  } else {
    noUiSlider.target.parentElement.querySelector(
      "span#upper-year",
    ).textContent = wNumb({ decimals: 0 }).to(parseFloat(values[1]));
  }
}
