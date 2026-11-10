/* ============================================
   Functions.js — App Logic
   Cover, particles, tap-through story, growing
   heart, timers and floating hearts
   ============================================ */

var $window = $(window), gardenCtx, gardenCanvas, $garden, $loveHeart, garden;

/* --- Environment Helpers --- */
var isMobile = (function () {
	return window.innerWidth <= 768 || ('ontouchstart' in window);
})();

var reducedMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

/* Cap at 2x — sharp on retina without quadrupling the pixels on 3x phones */
var pixelRatio = Math.min(window.devicePixelRatio || 1, 2);

/* --- Floating Particle / Sparkle System --- */
var particleCanvas, particleCtx, particles = [];
var particleLastTime = 0;
var viewW = window.innerWidth, viewH = window.innerHeight;

function initParticles() {
	particleCanvas = document.getElementById("particleCanvas");
	if (!particleCanvas) return;
	particleCtx = particleCanvas.getContext("2d");
	resizeParticleCanvas();

	// Create initial particles — fewer on mobile for performance
	var maxParticles = isMobile ? 50 : 120;
	if (reducedMotion) maxParticles = 30;
	var count = Math.min(Math.floor(viewW * viewH / 8000), maxParticles);
	for (var i = 0; i < count; i++) {
		particles.push(createParticle());
	}
	requestAnimationFrame(animateParticles);

	if (!reducedMotion) {
		setTimeout(spawnComet, 5000);
	}
}

function resizeParticleCanvas() {
	if (!particleCanvas) return;
	viewW = window.innerWidth;
	viewH = window.innerHeight;
	particleCanvas.width = Math.round(viewW * pixelRatio);
	particleCanvas.height = Math.round(viewH * pixelRatio);
	particleCtx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
}

function createParticle(options) {
	var types = ['circle', 'star'];
	var defaults = {
		x: Math.random() * viewW,
		y: Math.random() * viewH,
		size: Math.random() * 2.2 + 0.4,
		speedX: (Math.random() - 0.5) * 0.3,
		speedY: -Math.random() * 0.4 - 0.1,
		opacity: Math.random() * 0.5 + 0.1,
		opacitySpeed: (Math.random() - 0.5) * 0.008,
		type: types[Math.floor(Math.random() * types.length)],
		hue: Math.random() * 40 + 15, // warm gold range (15-55)
		life: -1, // -1 = infinite
		drag: 0.985,
		isBurst: false
	};
	if (options) {
		for (var key in options) {
			defaults[key] = options[key];
		}
	}
	return defaults;
}

/* --- Particle Burst ---
   x, y           : origin in viewport coordinates (the canvas is fixed)
   hueOptions     : array of hue values for the first wave
   shimmerHueBase : base hue for the delayed shimmer wave
*/
function triggerBurstAt(x, y, hueOptions, shimmerHueBase) {
	var burstCount = isMobile ? 40 : 80;
	for (var i = 0; i < burstCount; i++) {
		var angle = (Math.PI * 2 / burstCount) * i + (Math.random() - 0.5) * 0.4;
		var speed = Math.random() * 3 + 1.5;
		var hue = hueOptions[Math.floor(Math.random() * hueOptions.length)] + Math.random() * 15;

		particles.push(createParticle({
			x: x + (Math.random() - 0.5) * 60,
			y: y + (Math.random() - 0.5) * 30,
			size: Math.random() * 3.5 + 1,
			speedX: Math.cos(angle) * speed,
			speedY: Math.sin(angle) * speed - 0.5,
			opacity: 0.8 + Math.random() * 0.2,
			opacitySpeed: -0.008 - Math.random() * 0.006,
			type: Math.random() > 0.4 ? 'star' : 'circle',
			hue: hue,
			life: 3000 + Math.random() * 2000,
			isBurst: true
		}));
	}

	// Second wave — delayed gentle shimmer
	var shimmerCount = isMobile ? 20 : 40;
	setTimeout(function () {
		for (var i = 0; i < shimmerCount; i++) {
			var angle = Math.random() * Math.PI * 2;
			var speed = Math.random() * 1.5 + 0.5;
			particles.push(createParticle({
				x: x + (Math.random() - 0.5) * 200,
				y: y + (Math.random() - 0.5) * 200,
				size: Math.random() * 2 + 0.8,
				speedX: Math.cos(angle) * speed * 0.3,
				speedY: -Math.random() * 0.8 - 0.3,
				opacity: 0.6 + Math.random() * 0.3,
				opacitySpeed: -0.004 - Math.random() * 0.003,
				type: 'star',
				hue: shimmerHueBase + Math.random() * 40,
				life: 4000 + Math.random() * 2000,
				isBurst: true
			}));
		}
	}, 800);
}

/* Burst from the centre of an element (screen centre if it is missing) */
function triggerRevealBurst(elementId, hueOptions, shimmerHueBase) {
	var x = viewW / 2;
	var y = viewH / 2;
	var el = elementId ? document.getElementById(elementId) : null;
	if (el) {
		var rect = el.getBoundingClientRect();
		x = rect.left + rect.width / 2;
		y = rect.top + rect.height / 2;
	}
	triggerBurstAt(x, y, hueOptions, shimmerHueBase);
}

function triggerDaivikBurst() {
	// Warm: pinks, reds, golds
	triggerRevealBurst("daivikReveal", [340, 350, 0, 10, 20, 30, 40, 50], 15);
}

function triggerDeeyanBurst() {
	// Lavender / mauve — bridges the rose palette and stays distinct from Daivik's gold
	triggerRevealBurst("deeyanReveal", [250, 262, 275, 288, 300, 315], 265);
}

/* --- Finale shimmer: gentle gold-rose shower across the full screen --- */
function triggerFinaleShimmer() {
	var shimmerCount = isMobile ? 30 : 70;
	for (var i = 0; i < shimmerCount; i++) {
		setTimeout(function () {
			var hueOpts = [340, 350, 0, 20, 40, 300, 310];
			var hue = hueOpts[Math.floor(Math.random() * hueOpts.length)];
			particles.push(createParticle({
				x: Math.random() * viewW,
				y: Math.random() * viewH,
				size: Math.random() * 3 + 0.8,
				speedX: (Math.random() - 0.5) * 0.6,
				speedY: -Math.random() * 0.6 - 0.2,
				opacity: 0.7 + Math.random() * 0.3,
				opacitySpeed: -0.003 - Math.random() * 0.003,
				type: 'star',
				hue: hue,
				life: 5000 + Math.random() * 3000,
				isBurst: true
			}));
		}, Math.random() * 2000);
	}
}

/* --- Shooting star: one crosses the upper sky every so often --- */
function spawnComet() {
	if (!document.hidden) {
		var dir = Math.random() > 0.5 ? 1 : -1;
		particles.push(createParticle({
			x: viewW * (0.5 - dir * (0.1 + Math.random() * 0.4)),
			y: Math.random() * viewH * 0.3,
			size: 1.4,
			speedX: dir * (7 + Math.random() * 4),
			speedY: 2.5 + Math.random() * 2,
			opacity: 0.9,
			opacitySpeed: -0.014,
			type: 'comet',
			hue: 35,
			life: 1500,
			drag: 1,
			isBurst: true
		}));
	}
	setTimeout(spawnComet, 8000 + Math.random() * 10000);
}

function animateParticles(timestamp) {
	if (!particleCtx) return;

	var delta = particleLastTime ? Math.min(timestamp - particleLastTime, 64) : 16;
	var step = delta / 16;
	particleLastTime = timestamp;

	particleCtx.clearRect(0, 0, viewW, viewH);

	for (var i = particles.length - 1; i >= 0; i--) {
		var p = particles[i];

		p.x += p.speedX * step;
		p.y += p.speedY * step;

		// Burst particles decelerate and fade using real delta time
		if (p.isBurst) {
			p.speedX *= p.drag;
			p.speedY *= p.drag;
			p.life -= delta;
			p.opacity += p.opacitySpeed * step;
			if (p.life <= 0 || p.opacity <= 0) {
				// swap-with-last for O(1) removal
				particles[i] = particles[particles.length - 1];
				particles.pop();
				continue;
			}
		} else {
			p.opacity += p.opacitySpeed;
			if (p.opacity <= 0.05 || p.opacity >= 0.6) {
				p.opacitySpeed *= -1;
			}
			// Wrap around
			if (p.y < -10) { p.y = viewH + 10; p.x = Math.random() * viewW; }
			if (p.x < -10) p.x = viewW + 10;
			if (p.x > viewW + 10) p.x = -10;
		}

		// Draw
		particleCtx.save();
		particleCtx.globalAlpha = Math.max(0, Math.min(1, p.opacity));

		if (p.type === 'star') {
			drawStar(particleCtx, p.x, p.y, p.size, p.hue);
		} else if (p.type === 'comet') {
			drawComet(particleCtx, p);
		} else {
			particleCtx.beginPath();
			particleCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
			particleCtx.fillStyle = 'hsla(' + p.hue + ', 50%, 75%, 1)';
			particleCtx.shadowColor = 'hsla(' + p.hue + ', 50%, 75%, 0.5)';
			particleCtx.shadowBlur = isMobile ? (p.isBurst ? 6 : 3) : (p.isBurst ? 14 : 8);
			particleCtx.fill();
		}

		particleCtx.restore();
	}

	requestAnimationFrame(animateParticles);
}

function drawStar(ctx, x, y, size, hue) {
	var spikes = 4;
	var outerRadius = size * 2;
	var innerRadius = size * 0.8;
	var rot = Math.PI / 2 * 3;
	var step = Math.PI / spikes;

	ctx.beginPath();
	ctx.moveTo(x, y - outerRadius);

	for (var i = 0; i < spikes; i++) {
		ctx.lineTo(x + Math.cos(rot) * outerRadius, y + Math.sin(rot) * outerRadius);
		rot += step;
		ctx.lineTo(x + Math.cos(rot) * innerRadius, y + Math.sin(rot) * innerRadius);
		rot += step;
	}

	ctx.lineTo(x, y - outerRadius);
	ctx.closePath();
	ctx.fillStyle = 'hsla(' + hue + ', 45%, 80%, 1)';
	ctx.shadowColor = 'hsla(' + hue + ', 45%, 80%, 0.6)';
	ctx.shadowBlur = isMobile ? 4 : 10;
	ctx.fill();
}

function drawComet(ctx, p) {
	var tailX = p.x - p.speedX * 12;
	var tailY = p.y - p.speedY * 12;
	var gradient = ctx.createLinearGradient(p.x, p.y, tailX, tailY);
	gradient.addColorStop(0, 'hsla(' + p.hue + ', 70%, 90%, 1)');
	gradient.addColorStop(1, 'hsla(' + p.hue + ', 70%, 90%, 0)');
	ctx.beginPath();
	ctx.moveTo(p.x, p.y);
	ctx.lineTo(tailX, tailY);
	ctx.strokeStyle = gradient;
	ctx.lineWidth = p.size;
	ctx.lineCap = 'round';
	ctx.stroke();
}

/* --- Heart: canvas sizing + curve --- */

/* Dynamic heart scale factors — computed from the laid-out canvas size */
var heartScaleX, heartScaleY, offsetX, offsetY;
var heartW = 0, heartH = 0;

/* Bloom sizes were tuned for the 620x580 reference design */
var HEART_REF_WIDTH = 620;

function computeHeartMetrics() {
	var w = heartW;
	var h = heartH;

	// Exact bounding box of the parametric heart curve
	// (x = 16*sin^3(b), y = -(13cos(b)-5cos(2b)-2cos(3b)-cos(4b)))
	// X is symmetric: [-16, 16], Y range: [-11.9233, 17.0]
	var normHalfW = 16;          // half-width of normalised heart
	var normMinY  = -11.9233;    // top of normalised heart
	var normMaxY  =  17.0;       // bottom of normalised heart
	var normH     = normMaxY - normMinY; // 28.9233

	var pad = Math.min(w, h) * 0.05; // ~5% of the shorter side as margin

	// Scale uniformly so the heart fills the canvas while preserving its shape
	var scaleByW = (w - 2 * pad) / (2 * normHalfW);
	var scaleByH = (h - 2 * pad) / normH;
	var s = Math.min(scaleByW, scaleByH);

	heartScaleX = s;
	heartScaleY = s;

	// Centre horizontally; pin top of heart to the top padding
	offsetX = w / 2;
	offsetY = pad - s * normMinY; // maps normMinY → pad (top edge)
}

/* Size the canvas from the CSS-laid-out #loveHeart box. Whatever has
   already bloomed is carried over, so rotating a phone or resizing the
   window never wipes the heart. */
function sizeCanvas() {
	var w = $loveHeart.width();
	var h = $loveHeart.height();
	if (!w || !h || (w === heartW && h === heartH)) return;

	var snapshot = null;
	var ratio = 1;
	if (heartW && gardenCanvas.width) {
		snapshot = document.createElement("canvas");
		snapshot.width = gardenCanvas.width;
		snapshot.height = gardenCanvas.height;
		snapshot.getContext("2d").drawImage(gardenCanvas, 0, 0);
		ratio = w / heartW;
	}

	heartW = w;
	heartH = h;
	gardenCanvas.width = Math.round(w * pixelRatio);
	gardenCanvas.height = Math.round(h * pixelRatio);
	// Setting width/height resets the context, so state is (re)applied here
	gardenCtx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
	gardenCtx.globalCompositeOperation = "lighter";
	computeHeartMetrics();

	// Keep the flowers in proportion to the heart
	var bloomScale = Math.max(0.5, w / HEART_REF_WIDTH);
	Garden.options.bloomRadius.min = 8 * bloomScale;
	Garden.options.bloomRadius.max = 12 * bloomScale;
	Garden.options.lineWidth = Math.max(0.8, 1.2 * bloomScale);

	if (snapshot) {
		gardenCtx.drawImage(snapshot, 0, 0, w, h);
		garden.rescale(ratio);
		for (var i = 0; i < heartPoints.length; i++) {
			heartPoints[i][0] *= ratio;
			heartPoints[i][1] *= ratio;
		}
	}

	adjustWordsPosition();
	updateHeartClip();
}

/* Clip the photo layer to the same curve the flowers follow, pulled in
   slightly so its edge sits under the blooms. */
function updateHeartClip() {
	var el = document.getElementById("heartPhoto");
	if (!el || !heartW) return;
	var inset = 0.97;
	var centreY = offsetY + heartScaleY * 2.54; // middle of the curve's bounding box
	var points = [];
	for (var i = 0; i < 72; i++) {
		var p = getHeartPoint(Math.PI * 2 * i / 72);
		var x = offsetX + (p[0] - offsetX) * inset;
		var y = centreY + (p[1] - centreY) * inset;
		points.push((x / heartW * 100).toFixed(2) + '% ' + (y / heartH * 100).toFixed(2) + '%');
	}
	var value = 'polygon(' + points.join(', ') + ')';
	el.style.webkitClipPath = value;
	el.style.clipPath = value;
}

/* Point on the heart curve. b is the curve angle in radians:
   PI is the bottom tip, 0 (and 2*PI) the dip at the top. */
function getHeartPoint(b) {
	var a = heartScaleX * (16 * Math.pow(Math.sin(b), 3));
	var d = -heartScaleY * (13 * Math.cos(b) - 5 * Math.cos(2 * b) - 2 * Math.cos(3 * b) - Math.cos(4 * b));
	return new Array(offsetX + a, offsetY + d);
}

/* --- Heart: grows with the story ---
   Two lines of flowers start at the bottom tip and climb either side,
   a little further with every scene, and meet at the top at the finale. */
var heartProgress = 0;   // how much is planted, 0..1
var heartTarget = 0;     // how much the story has asked for, 0..1
var heartPoints = [];
var heartTimer = null;
var heartComplete = false;

function plantBloom(b) {
	var h = getHeartPoint(b);
	var minGap = Garden.options.bloomRadius.max * 1.3;
	for (var i = 0; i < heartPoints.length; i++) {
		var g = heartPoints[i];
		if (Math.sqrt(Math.pow(g[0] - h[0], 2) + Math.pow(g[1] - h[1], 2)) < minGap) {
			return;
		}
	}
	heartPoints.push(h);
	garden.createRandomBloom(h[0], h[1]);
}

function heartTick() {
	if (heartProgress < heartTarget) {
		heartProgress = Math.min(heartProgress + 0.004, heartTarget, 1);
		var sweep = Math.PI * heartProgress;
		plantBloom(Math.PI + sweep);
		plantBloom(Math.PI - sweep);
	}
	if (heartProgress >= 1 && !heartComplete) {
		heartComplete = true;
		completeHeart();
	}
	if (heartProgress >= heartTarget || heartComplete) {
		clearInterval(heartTimer);
		heartTimer = null;
	}
}

function growHeartTo(target) {
	if (target > heartTarget) heartTarget = Math.min(target, 1);
	if (!heartTimer && !heartComplete && heartProgress < heartTarget) {
		heartTimer = setInterval(heartTick, 50);
	}
}

function completeHeart() {
	// A burst where the two sides meet
	var rect = gardenCanvas.getBoundingClientRect();
	var top = getHeartPoint(0);
	triggerBurstAt(rect.left + top[0], rect.top + top[1], [340, 350, 0, 15, 30, 45], 20);
	$loveHeart.addClass("complete");
	showMessages();
}

function resetHeart() {
	if (heartTimer) clearInterval(heartTimer);
	heartTimer = null;
	heartProgress = 0;
	heartTarget = 0;
	heartPoints = [];
	heartComplete = false;
	garden.clear();
	$loveHeart.removeClass("complete");
	$("body").removeClass("finished");
}

/* --- Main Initialization --- */
$(function () {
	initParticles();
	initFloatingHearts();

	$loveHeart = $("#loveHeart");
	$garden = $("#garden");
	gardenCanvas = $garden[0];
	gardenCtx = gardenCanvas.getContext("2d");
	garden = new Garden(gardenCtx, gardenCanvas);

	// Size canvas to match the CSS-laid-out container
	sizeCanvas();

	// rAF so rendering syncs with display refresh and pauses in a background tab
	function gardenRenderLoop() {
		garden.render();
		requestAnimationFrame(gardenRenderLoop);
	}
	requestAnimationFrame(gardenRenderLoop);
});

var resizeTimer;
$(window).resize(function () {
	clearTimeout(resizeTimer);
	resizeTimer = setTimeout(function () {
		isMobile = window.innerWidth <= 768 || ('ontouchstart' in window);
		resizeParticleCanvas();
		if (gardenCanvas) {
			sizeCanvas();
		}
	}, 250);
});

/* --- Cover: the story waits until it is opened --- */
function initCover(specialDays, onOpen) {
	var today = new Date();
	for (var i = 0; i < specialDays.length; i++) {
		if (specialDays[i].month === today.getMonth() + 1 && specialDays[i].day === today.getDate()) {
			$("#coverNote").text(specialDays[i].note);
		}
	}

	var opened = false;
	$("#openBtn").click(function () {
		if (opened) return;
		opened = true;
		$("body").addClass("opened");
		// The heart column may have been laid out differently behind the cover
		sizeCanvas();
		setTimeout(onOpen, 1300);
		setTimeout(function () {
			$("#cover").css("display", "none");
		}, 1400);
	});
}

/* --- Story ---
   A tap-through sequence of scenes, one moment per screen.

   Markup contract, inside #stage:
     .scene                  one moment; its children appear one after another
     data-day / data-year    on a .scene — the date shown inside the heart
     data-photo="name"       on a .scene — images/photos/name.jpg, shown inside
                             the heart if that file exists (silently skipped if not)
     .code                   typed out character by character
     [data-reveal="name"]    glow + particle burst when it appears
*/
var storyScenes = [];
var sceneIndex = -1;
var scenePieces = [];
var pieceIndex = 0;
var sceneBusy = false;
var sceneTimer = null;
var hintTimer = null;
var storyStarted = false;
var photoCache = {};
var photoShown = null;
var photoFront = 0;

/* Remember each text node of a code block so it can be typed back in */
function prepareCode(el) {
	var steps = [];
	function collect(node) {
		for (var i = 0; i < node.childNodes.length; i++) {
			var child = node.childNodes[i];
			if (child.nodeType === 3 && child.nodeValue.length) {
				steps.push({ node: child, text: child.nodeValue });
			} else if (child.nodeType === 1) {
				collect(child);
			}
		}
	}
	collect(el);
	el.typeSteps = steps;
	el.typeCursor = document.createElement("span");
	el.typeCursor.className = "cursor";
}

function setCode(el, full) {
	for (var i = 0; i < el.typeSteps.length; i++) {
		el.typeSteps[i].node.nodeValue = full ? el.typeSteps[i].text : '';
	}
	if (full && el.typeSteps.length) {
		var last = el.typeSteps[el.typeSteps.length - 1].node;
		last.parentNode.insertBefore(el.typeCursor, last.nextSibling);
	}
}

function typeCode(el, done) {
	var stepIndex = 0;
	var charIndex = 0;
	function tick() {
		if (stepIndex >= el.typeSteps.length) {
			done();
			return;
		}
		var step = el.typeSteps[stepIndex];
		if (charIndex === 0) {
			step.node.parentNode.insertBefore(el.typeCursor, step.node.nextSibling);
		}
		charIndex++;
		step.node.nodeValue = step.text.substring(0, charIndex);
		if (charIndex >= step.text.length) {
			stepIndex++;
			charIndex = 0;
		}
		sceneTimer = setTimeout(tick, 22 + Math.random() * 30);
	}
	setCode(el, false);
	tick();
}

function revealName(el) {
	if ($(el).hasClass("revealed")) return;
	$(el).addClass("revealed");
	var name = el.getAttribute("data-reveal");
	if (name === 'daivik') triggerDaivikBurst();
	if (name === 'deeyan') triggerDeeyanBurst();
}

function resetScene(scene) {
	$(scene).children().removeClass("in");
	$(scene).find("[data-reveal]").removeClass("revealed");
	$(scene).find(".code").each(function () {
		setCode(this, false);
	});
}

/* --- The date inside the heart --- */
function setHeartDate(day, year) {
	var $date = $("#heartDate");
	$date.addClass("changing");
	setTimeout(function () {
		$("#dateDay").html(day || '');
		$("#dateYear").html(year || '');
		if (day || year) $date.removeClass("changing");
	}, 450);
}

/* --- Optional photos inside the heart --- */
function preloadPhotos() {
	$("#stage .scene").each(function () {
		var name = this.getAttribute("data-photo");
		if (!name || photoCache[name] !== undefined) return;
		photoCache[name] = null;
		var img = new Image();
		img.onload = function () {
			photoCache[name] = img.src;
			// It may have arrived while its scene is already on screen
			var scene = storyScenes[sceneIndex];
			if (scene && scene.getAttribute("data-photo") === name) setHeartPhoto(name);
		};
		img.src = "images/photos/" + name + ".jpg";
	});
}

function setHeartPhoto(name) {
	var src = (name && photoCache[name]) || null;
	if (src === photoShown) return;
	photoShown = src;
	var $layers = $("#heartPhoto .photo-layer");
	$layers.eq(photoFront).removeClass("show");
	if (src) {
		photoFront = 1 - photoFront;
		$layers.eq(photoFront).css("background-image", 'url("' + src + '")').addClass("show");
		$loveHeart.addClass("has-photo");
	} else {
		$loveHeart.removeClass("has-photo");
	}
}

/* --- Moving between scenes --- */
function showHint() {
	clearTimeout(hintTimer);
	if (sceneIndex >= storyScenes.length - 1) {
		$("#hint").text("hold anywhere to send hearts");
	} else {
		$("#hint").text(isMobile ? "tap to continue" : "click to continue");
	}
	hintTimer = setTimeout(function () {
		$("#hint").addClass("show");
	}, sceneIndex === 0 ? 600 : 2200);
}

function nextPiece() {
	if (pieceIndex >= scenePieces.length) {
		sceneBusy = false;
		showHint();
		return;
	}
	var el = scenePieces[pieceIndex++];
	$(el).addClass("in");
	if (el.getAttribute("data-reveal")) {
		setTimeout(function () {
			if ($(el).hasClass("in")) revealName(el);
		}, 500);
		sceneTimer = setTimeout(nextPiece, 1700);
	} else if ($(el).hasClass("code")) {
		sceneTimer = setTimeout(function () {
			typeCode(el, function () {
				sceneTimer = setTimeout(nextPiece, 300);
			});
		}, 500);
	} else {
		sceneTimer = setTimeout(nextPiece, 800);
	}
}

/* A tap while a scene is still arriving shows the rest of it at once */
function rushScene() {
	clearTimeout(sceneTimer);
	for (var i = 0; i < scenePieces.length; i++) {
		var el = scenePieces[i];
		$(el).addClass("in");
		if ($(el).hasClass("code")) setCode(el, true);
		if (el.getAttribute("data-reveal")) revealName(el);
	}
	pieceIndex = scenePieces.length;
	sceneBusy = false;
	showHint();
}

function goToScene(index) {
	if (index < 0 || index >= storyScenes.length || index === sceneIndex) return;
	clearTimeout(sceneTimer);
	clearTimeout(hintTimer);
	$("#hint").removeClass("show");

	var old = storyScenes[sceneIndex];
	if (old) {
		$(old).removeClass("active").addClass("leaving");
		setTimeout(function () {
			$(old).removeClass("leaving");
			if (storyScenes[sceneIndex] !== old) resetScene(old);
		}, 600);
	}

	sceneIndex = index;
	var scene = storyScenes[index];
	resetScene(scene);
	$(scene).removeClass("leaving").addClass("active");
	$("#dots span").removeClass("on").eq(index).addClass("on");

	setHeartDate(scene.getAttribute("data-day"), scene.getAttribute("data-year"));
	setHeartPhoto(scene.getAttribute("data-photo"));
	// The heart closes on the second-to-last scene; the last one is the sign-off
	growHeartTo(Math.min(1, (index + 1) / (storyScenes.length - 1)));

	scenePieces = $(scene).children().get();
	pieceIndex = 0;
	sceneBusy = true;
	sceneTimer = setTimeout(nextPiece, reducedMotion ? 0 : 650);
	if (reducedMotion) rushScene();
}

function advanceStory() {
	if (!storyStarted) return;
	if (sceneBusy) {
		rushScene();
	} else {
		goToScene(sceneIndex + 1);
	}
}

function replayStory() {
	resetHeart();
	goToScene(0);
}

function initStory() {
	var dots = '';
	$("#stage .scene").each(function () {
		storyScenes.push(this);
		$(this).children().addClass("piece");
		dots += "<span></span>";
	});
	$("#dots").html(dots);
	$("#stage .code").each(function () {
		prepareCode(this);
		setCode(this, false);
	});
	preloadPhotos();

	// Anywhere on the page moves the story on (buttons look after themselves)
	$("#mainDiv").click(function (e) {
		if ($(e.target).closest("button").length) return;
		advanceStory();
	});
	$(document).keydown(function (e) {
		if (!storyStarted) return;
		if (e.keyCode === 39 || e.keyCode === 32) advanceStory();
		if (e.keyCode === 37 && sceneIndex > 0) goToScene(sceneIndex - 1);
	});
	$("#replayBtn").click(replayStory);
}

function startStory() {
	storyStarted = true;
	goToScene(0);
}

/* --- Time Elapsed --- */
function setText(id, value) {
	var el = document.getElementById(id);
	// Only touch the DOM when the value actually changed
	if (el && el.innerHTML !== String(value)) el.innerHTML = value;
}

function padTwo(n) {
	return n < 10 ? "0" + n : String(n);
}

function timeElapse(start) {
	var seconds = Math.max(0, Math.floor((new Date().getTime() - start.getTime()) / 1000));
	var days = Math.floor(seconds / 86400);
	seconds = seconds % 86400;
	var hours = Math.floor(seconds / 3600);
	seconds = seconds % 3600;
	var minutes = Math.floor(seconds / 60);
	seconds = seconds % 60;

	setText("elapseDays", String(days).replace(/\B(?=(\d{3})+$)/g, ","));
	setText("elapseHrs", padTwo(hours));
	setText("elapseMin", padTwo(minutes));
	setText("elapseSec", padTwo(seconds));
}

/* Calendar difference as [years, months, days] */
function calendarDiff(from, to) {
	var years = to.getFullYear() - from.getFullYear();
	var months = to.getMonth() - from.getMonth();
	var days = to.getDate() - from.getDate();
	if (days < 0) {
		months--;
		days += new Date(to.getFullYear(), to.getMonth(), 0).getDate();
	}
	if (months < 0) {
		years--;
		months += 12;
	}
	return [years, months, days];
}

/* Fills each milestone element with e.g. "3y 9m 15d" */
function updateMilestones(list) {
	var now = new Date();
	var units = ['y', 'm', 'd'];
	for (var i = 0; i < list.length; i++) {
		var diff = calendarDiff(list[i].date, now);
		var parts = [];
		for (var j = 0; j < 3; j++) {
			// Skip leading zeros ("2m 1d", not "0y 2m 1d") but always show days
			if (diff[j] > 0 || parts.length || j === 2) {
				parts.push("<b>" + diff[j] + "</b>" + units[j]);
			}
		}
		setText(list[i].id, parts.join(" "));
	}
}

/* --- Finale --- */
function showMessages() {
	adjustWordsPosition();
	// CSS takes it from here: the date gives way to the running count
	$("body").addClass("finished");
}

/* Scale the words inside the heart with the heart itself (proportional, no fixed pixels) */
function adjustWordsPosition() {
	if (!heartW) return;
	$("#words, #heartDate").css("font-size", Math.max(10.5, heartW * 0.042) + "px");
}

/* --- Floating Hearts on Click / Touch + Idle --- */
var heartLayer, floatingHearts = [];
var pointerDown = false, pointerX = 0, pointerY = 0;
var heartFrameRunning = false, heartLastTime = 0;
var HEART_LIFE = 3500;

function generateHeart(x, y) {
	if (!heartLayer) return;
	var el = document.createElement("div");
	el.className = "heart";
	heartLayer.appendChild(el);
	floatingHearts.push({
		el: el,
		x: x,
		y: y,
		age: 0,
		scale: (Math.random() * Math.random() * 0.6 + 0.35) * (isMobile ? 0.8 : 1),
		sway: 10 + Math.random() * 16,
		phase: Math.random() * Math.PI * 2,
		rise: 0.03 + Math.random() * 0.03
	});
	if (!heartFrameRunning) {
		heartFrameRunning = true;
		// Restart the clock so the first frame after idling isn't one huge step
		heartLastTime = Date.now();
		requestAnimationFrame(heartFrame);
	}
}

function heartFrame() {
	var now = Date.now();
	var delta = Math.min(now - heartLastTime, 64);
	heartLastTime = now;
	for (var i = floatingHearts.length - 1; i >= 0; i--) {
		var heart = floatingHearts[i];
		heart.age += delta;
		if (heart.age < HEART_LIFE) {
			var x = heart.x + Math.sin(heart.age / 450 + heart.phase) * heart.sway;
			var y = heart.y - heart.age * heart.rise;
			var value = 'translate(' + x + 'px,' + y + 'px) scale(' + heart.scale + ')';
			heart.el.style.webkitTransform = value;
			heart.el.style.transform = value;
			heart.el.style.opacity = 1 - heart.age / HEART_LIFE;
		} else {
			heartLayer.removeChild(heart.el);
			floatingHearts.splice(i, 1);
		}
	}
	if (floatingHearts.length > 0) {
		requestAnimationFrame(heartFrame);
	} else {
		heartFrameRunning = false;
	}
}

function initFloatingHearts() {
	heartLayer = document.createElement("div");
	heartLayer.id = "heartLayer";
	document.body.appendChild(heartLayer);

	function press(point) {
		pointerDown = true;
		pointerX = point.clientX;
		pointerY = point.clientY;
		generateHeart(pointerX, pointerY - 5);
	}
	function move(point) {
		pointerX = point.clientX;
		pointerY = point.clientY;
	}
	function release() {
		pointerDown = false;
	}

	document.addEventListener("mousedown", press);
	document.addEventListener("mousemove", move);
	document.addEventListener("mouseup", release);
	document.addEventListener("touchstart", function (e) { press(e.touches[0]); }, { passive: true });
	document.addEventListener("touchmove", function (e) { move(e.touches[0]); }, { passive: true });
	document.addEventListener("touchend", release);
	document.addEventListener("touchcancel", release);

	// A stream of hearts while holding down
	setInterval(function () {
		if (pointerDown) generateHeart(pointerX, pointerY - 5);
	}, 110);

	// Idle ambient hearts — one drifts up from the bottom every ~10 seconds
	if (!reducedMotion) {
		setInterval(function () {
			if (document.hidden) return;
			generateHeart(Math.random() * window.innerWidth, window.innerHeight + 10);
		}, 10000);
	}
}
