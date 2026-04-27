document.addEventListener("DOMContentLoaded", function () {
  var sliderContainers = document.querySelectorAll(".range-slider");
  if (!sliderContainers.length) return;

  sliderContainers.forEach(function (sliderContainer) {
    var MIN_YEAR = parseInt(sliderContainer.dataset.rangeStart) || 1800;
    var MAX_YEAR =
      parseInt(sliderContainer.dataset.rangeEnd) ||
      new Date().getFullYear() + 5;
    var STEP = 1;

    var startFormId = sliderContainer.dataset.startForm;
    var endFormId = sliderContainer.dataset.endForm;
    var showLimits = sliderContainer.dataset.showLimits !== "false";

    var startExclusiveId = sliderContainer.dataset.startExclusive || null;
    var endExclusiveId = sliderContainer.dataset.endExclusive || null;
    var subjectLabel = sliderContainer.dataset.subjectLabel || "Eintrag";

    if (!startFormId || !endFormId) return;

    var lowerExclusive = false;
    var upperExclusive = false;
    var sliderTouched = false;

    // Hidden range inputs (data stores only)
    var lower = document.createElement("input");
    var upper = document.createElement("input");

    [lower, upper].forEach(function (el) {
      el.type = "range";
      el.min = MIN_YEAR;
      el.max = MAX_YEAR;
      el.step = STEP;
      el.tabIndex = -1;
    });

    lower.value = MIN_YEAR;
    upper.value = MAX_YEAR;

    sliderContainer.appendChild(lower);
    sliderContainer.appendChild(upper);

    // Optional min/max labels
    if (showLimits) {
      var minLabel = document.createElement("span");
      minLabel.className = "range-slider__limit range-slider__limit--min";
      minLabel.textContent = MIN_YEAR;
      sliderContainer.appendChild(minLabel);

      var maxLabel = document.createElement("span");
      maxLabel.className = "range-slider__limit range-slider__limit--max";
      maxLabel.textContent = MAX_YEAR;
      sliderContainer.appendChild(maxLabel);
    }

    // Track bar
    var track = document.createElement("div");
    track.className = "range-slider__track";
    sliderContainer.appendChild(track);

    // Custom visual thumbs
    var thumbLower = document.createElement("div");
    var thumbUpper = document.createElement("div");
    thumbLower.className = "range-slider__thumb";
    thumbUpper.className = "range-slider__thumb";
    sliderContainer.appendChild(thumbLower);
    sliderContainer.appendChild(thumbUpper);

    // Tooltips
    var tooltipLower = document.createElement("div");
    var tooltipUpper = document.createElement("div");
    tooltipLower.className = "range-slider__tooltip";
    tooltipUpper.className = "range-slider__tooltip";
    sliderContainer.appendChild(tooltipLower);
    sliderContainer.appendChild(tooltipUpper);

    // Timeframe description beneath the slider (hidden until interaction)
    var timeframeDesc = document.createElement("div");
    timeframeDesc.className = "range-slider__timeframe";
    sliderContainer.appendChild(timeframeDesc);

    var tfPrefix = document.createTextNode("Ausgew\u00e4hlter Zeitraum: ");
    timeframeDesc.appendChild(tfPrefix);

    var startYearInput = document.createElement("input");
    startYearInput.type = "text";
    startYearInput.className = "range-slider__year-input";
    startYearInput.value = MIN_YEAR;
    timeframeDesc.appendChild(startYearInput);

    var tfMid = document.createTextNode(" \u2013 ");
    timeframeDesc.appendChild(tfMid);

    var endYearInput = document.createElement("input");
    endYearInput.type = "text";
    endYearInput.className = "range-slider__year-input";
    endYearInput.value = MAX_YEAR;
    timeframeDesc.appendChild(endYearInput);

    // Exclusive boundary info line (beneath the timeframe description)
    var exclusiveInfo = document.createElement("div");
    exclusiveInfo.className = "range-slider__exclusive-info";
    sliderContainer.appendChild(exclusiveInfo);

    function updateExclusiveInfo() {
      var parts = [];
      var lowVal = parseInt(lower.value);
      var upVal = parseInt(upper.value);
      if (lowerExclusive) {
        parts.push(subjectLabel + " muss nach " + (lowVal - 1) + " starten");
      }
      if (upperExclusive) {
        parts.push(subjectLabel + " muss vor " + (upVal + 1) + " enden");
      }
      if (parts.length > 0) {
        exclusiveInfo.textContent = parts.join(" / ");
        exclusiveInfo.classList.add("range-slider__exclusive-info--visible");
      } else {
        exclusiveInfo.textContent = "";
        exclusiveInfo.classList.remove("range-slider__exclusive-info--visible");
      }
    }

    function showTooltip(tt) {
      tt.classList.add("range-slider__tooltip--visible");
    }
    function hideTooltip(tt) {
      tt.classList.remove("range-slider__tooltip--visible");
    }

    // Hover tooltips on the custom thumbs
    thumbLower.addEventListener("mouseenter", function () {
      showTooltip(tooltipLower);
    });
    thumbLower.addEventListener("mouseleave", function () {
      if (!thumbLower._dragging) hideTooltip(tooltipLower);
    });
    thumbUpper.addEventListener("mouseenter", function () {
      showTooltip(tooltipUpper);
    });
    thumbUpper.addEventListener("mouseleave", function () {
      if (!thumbUpper._dragging) hideTooltip(tooltipUpper);
    });

    // Double-click on a thumb -> toggle exclusive
    function syncExclusiveField(fieldId, isExclusive) {
      if (!fieldId) return;
      var field = document.getElementById(fieldId);
      if (!field) return;
      field.checked = isExclusive;
      field.value = isExclusive ? "true" : "";
    }

    thumbLower.addEventListener("dblclick", function () {
      if (!startExclusiveId) return;
      lowerExclusive = !lowerExclusive;
      thumbLower.classList.toggle(
        "range-slider__thumb--exclusive",
        lowerExclusive,
      );
      syncExclusiveField(startExclusiveId, lowerExclusive);
      sliderTouched = true;
      updateExclusiveInfo();
    });

    thumbUpper.addEventListener("dblclick", function () {
      if (!endExclusiveId) return;
      upperExclusive = !upperExclusive;
      thumbUpper.classList.toggle(
        "range-slider__thumb--exclusive",
        upperExclusive,
      );
      syncExclusiveField(endExclusiveId, upperExclusive);
      sliderTouched = true;
      updateExclusiveInfo();
    });

    // Update UI + hidden form fields
    function update() {
      if (parseInt(lower.value) > parseInt(upper.value)) {
        var tmp = lower.value;
        lower.value = upper.value;
        upper.value = tmp;
      }

      var lowVal = parseInt(lower.value);
      var upVal = parseInt(upper.value);

      var percLow = ((lowVal - MIN_YEAR) / (MAX_YEAR - MIN_YEAR)) * 100;
      var percUp = ((upVal - MIN_YEAR) / (MAX_YEAR - MIN_YEAR)) * 100;
      thumbLower.style.left = percLow + "%";
      thumbUpper.style.left = percUp + "%";

      tooltipLower.textContent = lowVal;
      tooltipLower.style.left = percLow + "%";
      tooltipUpper.textContent = upVal;
      tooltipUpper.style.left = percUp + "%";

      track.style.background =
        "linear-gradient(to right, #ddd " +
        percLow +
        "%, #007bff " +
        percLow +
        "%, #007bff " +
        percUp +
        "%, #ddd " +
        percUp +
        "%)";

      // Update year inputs to reflect current slider values
      startYearInput.value = lowVal;
      endYearInput.value = upVal;

      // Show the timeframe description once the slider has been touched
      if (sliderTouched) {
        timeframeDesc.classList.add("range-slider__timeframe--visible");

        var startField = document.getElementById(startFormId);
        var endField = document.getElementById(endFormId);
        if (startField) startField.value = lowVal + "-01-01";
        if (endField) endField.value = upVal + "-12-31";
      }

      // Keep exclusive info in sync with current year values
      updateExclusiveInfo();
    }

    // Handle manual year input: parse, clamp, sync slider and form
    function onYearInput(inputEl, rangeInput) {
      var raw = inputEl.value.replace(/[^0-9]/g, "");
      if (raw.length === 0) return;
      var year = parseInt(raw, 10);
      if (isNaN(year)) return;
      year = Math.max(MIN_YEAR, Math.min(MAX_YEAR, year));
      rangeInput.value = year;
      sliderTouched = true;
      update();
    }

    startYearInput.addEventListener("change", function () {
      onYearInput(startYearInput, lower);
    });
    endYearInput.addEventListener("change", function () {
      onYearInput(endYearInput, upper);
    });

    // Drag handling on the custom thumb divs
    function clientXToValue(clientX) {
      var rect = sliderContainer.getBoundingClientRect();
      var ratio = (clientX - rect.left) / rect.width;
      ratio = Math.max(0, Math.min(1, ratio));
      var val = Math.round(MIN_YEAR + ratio * (MAX_YEAR - MIN_YEAR));
      val = Math.round(val / STEP) * STEP;
      return Math.max(MIN_YEAR, Math.min(MAX_YEAR, val));
    }

    function makeDraggable(thumbEl, rangeInput, tooltip) {
      function onStart(e) {
        e.preventDefault();
        thumbEl._dragging = true;
        sliderTouched = true;
        showTooltip(tooltip);

        function onMove(ev) {
          var clientX = ev.touches ? ev.touches[0].clientX : ev.clientX;
          rangeInput.value = clientXToValue(clientX);
          update();
        }

        function onEnd() {
          thumbEl._dragging = false;
          hideTooltip(tooltip);
          document.removeEventListener("mousemove", onMove);
          document.removeEventListener("mouseup", onEnd);
          document.removeEventListener("touchmove", onMove);
          document.removeEventListener("touchend", onEnd);
        }

        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onEnd);
        document.addEventListener("touchmove", onMove, { passive: false });
        document.addEventListener("touchend", onEnd);
      }

      thumbEl.addEventListener("mousedown", onStart);
      thumbEl.addEventListener("touchstart", onStart, { passive: false });
    }

    makeDraggable(thumbLower, lower, tooltipLower);
    makeDraggable(thumbUpper, upper, tooltipUpper);

    // Initial render
    update();
  });
});
