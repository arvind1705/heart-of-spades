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

/* Return ambient particle hues tuned to the active chapter and theme */
function getChapterHues() {
	var tint = document.body ? (document.body.getAttribute("data-tint") || "intro") : "intro";
	var isChampagne = document.body && document.body.getAttribute("data-theme") === "champagne";
	if (isChampagne) {
		if (tint === "deeyan") return [265, 280, 340, 38];
		return [335, 348, 25, 38, 275];
	}
	if (tint === "love" || tint === "proposal") return [332, 342, 352, 280, 15];
	if (tint === "wedding") return [338, 350, 22, 38, 275];
	if (tint === "daivik") return [342, 16, 28, 40, 325];
	if (tint === "deeyan") return [248, 264, 280, 300, 332];
	if (tint === "finale") return [334, 348, 268, 290, 22];
	return [334, 346, 262, 284, 18];
}

function pickChapterHue() {
	var hues = getChapterHues();
	return hues[Math.floor(Math.random() * hues.length)] + (Math.random() - 0.5) * 10;
}

function createParticle(options) {
	var r = Math.random();
	var type = r < 0.16 ? 'petal' : (r < 0.58 ? 'star' : 'circle');
	var defaults = {
		x: Math.random() * viewW,
		y: Math.random() * viewH,
		size: type === 'petal' ? (Math.random() * 2.8 + 2.2) : (Math.random() * 2.2 + 0.4),
		speedX: (Math.random() - 0.5) * 0.3,
		speedY: type === 'petal' ? (-Math.random() * 0.28 - 0.08) : (-Math.random() * 0.4 - 0.1),
		opacity: type === 'petal' ? (Math.random() * 0.32 + 0.12) : (Math.random() * 0.5 + 0.1),
		opacitySpeed: (Math.random() - 0.5) * 0.008,
		type: type,
		hue: pickChapterHue(),
		angle: Math.random() * Math.PI * 2,
		spin: (Math.random() - 0.5) * 0.025,
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
			type: Math.random() > 0.35 ? 'star' : (Math.random() > 0.3 ? 'circle' : 'petal'),
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

/* Soft chapter celebration shimmer (used for proposal & wedding milestones) */
function triggerMilestoneShimmer(hueOpts) {
	if (reducedMotion) return;
	var count = isMobile ? 18 : 36;
	for (var i = 0; i < count; i++) {
		(function () {
			setTimeout(function () {
				var hue = hueOpts[Math.floor(Math.random() * hueOpts.length)] + (Math.random() - 0.5) * 10;
				particles.push(createParticle({
					x: viewW * (0.15 + Math.random() * 0.7),
					y: viewH * (0.2 + Math.random() * 0.65),
					size: Math.random() * 2.4 + 0.9,
					speedX: (Math.random() - 0.5) * 0.5,
					speedY: -Math.random() * 0.7 - 0.25,
					opacity: 0.75 + Math.random() * 0.25,
					opacitySpeed: -0.004 - Math.random() * 0.003,
					type: Math.random() > 0.25 ? 'star' : 'petal',
					hue: hue,
					life: 3600 + Math.random() * 2000,
					isBurst: true
				}));
			}, Math.random() * 1100);
		})();
	}
}

/* --- Finale shimmer: gentle gold-rose shower across the full screen --- */
function triggerFinaleShimmer() {
	if (reducedMotion) return;
	var shimmerCount = isMobile ? 32 : 70;
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
				type: Math.random() > 0.25 ? 'star' : 'petal',
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
		var cometHues = [338, 265, 225, 350];
		particles.push(createParticle({
			x: viewW * (0.5 - dir * (0.1 + Math.random() * 0.4)),
			y: Math.random() * viewH * 0.3,
			size: 1.4,
			speedX: dir * (7 + Math.random() * 4),
			speedY: 2.5 + Math.random() * 2,
			opacity: 0.92,
			opacitySpeed: -0.014,
			type: 'comet',
			hue: cometHues[Math.floor(Math.random() * cometHues.length)],
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

	// Subtle firefly twinkles along the already-bloomed heart wreath
	if (!reducedMotion && storyStarted && heartPoints.length > 4 && gardenCanvas && Math.random() < (isMobile ? 0.035 : 0.065)) {
		var hp = heartPoints[Math.floor(Math.random() * heartPoints.length)];
		var gRect = gardenCanvas.getBoundingClientRect();
		particles.push(createParticle({
			x: gRect.left + hp[0] + (Math.random() - 0.5) * 10,
			y: gRect.top + hp[1] + (Math.random() - 0.5) * 10,
			size: Math.random() * 1.6 + 0.7,
			speedX: (Math.random() - 0.5) * 0.25,
			speedY: -Math.random() * 0.35 - 0.08,
			opacity: 0.75,
			opacitySpeed: -0.012,
			type: 'star',
			hue: pickChapterHue(),
			life: 1400 + Math.random() * 900,
			isBurst: true
		}));
	}

	for (var i = particles.length - 1; i >= 0; i--) {
		var p = particles[i];

		p.x += p.speedX * step;
		p.y += p.speedY * step;
		if (p.type === 'petal') {
			p.angle += p.spin * step;
			p.x += Math.sin(p.angle * 0.7) * 0.15 * step;
		}

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
			var maxOp = p.type === 'petal' ? 0.42 : 0.6;
			if (p.opacity <= 0.05 || p.opacity >= maxOp) {
				p.opacitySpeed *= -1;
			}
			// Wrap around and refresh hue to match current chapter
			if (p.y < -12) {
				p.y = viewH + 12;
				p.x = Math.random() * viewW;
				p.hue = pickChapterHue();
			}
			if (p.x < -12) p.x = viewW + 12;
			if (p.x > viewW + 12) p.x = -12;
		}

		// Draw
		particleCtx.save();
		particleCtx.globalAlpha = Math.max(0, Math.min(1, p.opacity));

		if (p.type === 'star') {
			drawStar(particleCtx, p.x, p.y, p.size, p.hue);
		} else if (p.type === 'petal') {
			drawPetal(particleCtx, p);
		} else if (p.type === 'comet') {
			drawComet(particleCtx, p);
		} else {
			particleCtx.beginPath();
			particleCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
			particleCtx.fillStyle = 'hsla(' + p.hue + ', 68%, 82%, 1)';
			particleCtx.shadowColor = 'hsla(' + p.hue + ', 72%, 78%, 0.55)';
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
	ctx.fillStyle = 'hsla(' + hue + ', 65%, 86%, 1)';
	ctx.shadowColor = 'hsla(' + hue + ', 70%, 82%, 0.65)';
	ctx.shadowBlur = isMobile ? 4 : 10;
	ctx.fill();
}

function drawPetal(ctx, p) {
	var s = p.size;
	ctx.translate(p.x, p.y);
	ctx.rotate(p.angle);
	ctx.beginPath();
	ctx.moveTo(0, -s);
	ctx.bezierCurveTo(s * 0.95, -s * 0.35, s * 0.85, s * 0.75, 0, s);
	ctx.bezierCurveTo(-s * 0.85, s * 0.75, -s * 0.95, -s * 0.35, 0, -s);
	ctx.closePath();
	ctx.fillStyle = 'hsla(' + p.hue + ', 72%, 80%, 0.85)';
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

	// Keep the flowers in proportion to the heart and preserve petal stroke density on mobile
	var bloomScale = Math.max(0.58, w / HEART_REF_WIDTH);
	Garden.options.bloomRadius.min = 7.5 * bloomScale;
	Garden.options.bloomRadius.max = 15.5 * bloomScale;
	Garden.options.growFactor.min = 0.09 * bloomScale;
	Garden.options.growFactor.max = 0.85 * bloomScale;
	Garden.options.lineWidth = Math.max(1.0, 1.5 * bloomScale);

	if (snapshot) {
		gardenCtx.drawImage(snapshot, 0, 0, w, h);
		garden.rescale(ratio);
		for (var i = 0; i < heartPoints.length; i++) {
			heartPoints[i][0] *= ratio;
			heartPoints[i][1] *= ratio;
		}
	}

	adjustWordsPosition();
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
	var minGap = Garden.options.bloomRadius.max * 0.82;
	for (var i = 0; i < heartPoints.length; i++) {
		var g = heartPoints[i];
		if (Math.sqrt(Math.pow(g[0] - h[0], 2) + Math.pow(g[1] - h[1], 2)) < minGap) {
			return;
		}
	}
	heartPoints.push(h);
	var jitterX = (Math.random() - 0.5) * 2.2;
	var jitterY = (Math.random() - 0.5) * 2.2;
	garden.createRandomBloom(h[0] + jitterX, h[1] + jitterY);

	// Occasional delicate accent bud beside the main bloom for a fuller garland
	if (Math.random() < 0.38) {
		var budOffset = Garden.options.bloomRadius.min * 0.55;
		var budAngle = Math.random() * Math.PI * 2;
		garden.createBloom(
			h[0] + Math.cos(budAngle) * budOffset,
			h[1] + Math.sin(budAngle) * budOffset,
			Garden.options.bloomRadius.min * 0.72,
			Garden.randomRomanticColor(),
			Garden.randomInt(6, 9),
			Garden.randomGlowColor()
		);
	}

	// Trailing stardust at the growing tips as the two sides climb
	if (!reducedMotion && storyStarted && gardenCanvas && Math.random() < 0.65) {
		var rect = gardenCanvas.getBoundingClientRect();
		particles.push(createParticle({
			x: rect.left + h[0] + (Math.random() - 0.5) * 8,
			y: rect.top + h[1] + (Math.random() - 0.5) * 8,
			size: Math.random() * 1.8 + 0.8,
			speedX: (Math.random() - 0.5) * 0.6,
			speedY: -Math.random() * 0.6 - 0.15,
			opacity: 0.85,
			opacitySpeed: -0.015,
			type: 'star',
			hue: pickChapterHue(),
			life: 1100 + Math.random() * 700,
			isBurst: true
		}));
	}
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
	// A burst where the two sides meet + full-screen celebratory shimmer
	var rect = gardenCanvas.getBoundingClientRect();
	var top = getHeartPoint(0);
	triggerBurstAt(rect.left + top[0], rect.top + top[1], [340, 350, 0, 15, 30, 45], 20);
	triggerFinaleShimmer();
	$loveHeart.addClass("complete");
	showMessages();
}

var finaleCounting = false;
var finaleCountToken = 0;

function resetHeart() {
	if (heartTimer) clearInterval(heartTimer);
	heartTimer = null;
	heartProgress = 0;
	heartTarget = 0;
	heartPoints = [];
	heartComplete = false;
	finaleCounting = false;
	finaleCountToken++;
	garden.clear();
	$loveHeart.removeClass("complete").removeClass("thump");
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
	Garden.theme = document.body.getAttribute("data-theme") === "champagne" ? "champagne" : "rose";
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

/* --- Themes: Midnight Rose by default, Champagne Dawn on special days --- */
function applyTheme(name) {
	if (name !== "champagne") name = "rose";
	document.body.setAttribute("data-theme", name);
	if (typeof Garden !== "undefined") Garden.theme = name;
}

/* --- Cover: the story waits until it is opened --- */
function initCover(specialDays, onOpen) {
	var today = new Date();
	for (var i = 0; i < specialDays.length; i++) {
		if (specialDays[i].month === today.getMonth() + 1 && specialDays[i].day === today.getDate()) {
			$("#coverNote").text(specialDays[i].note);
			if (specialDays[i].theme) applyTheme(specialDays[i].theme);
		}
	}

	var opened = false;
	$("#openBtn").click(function () {
		if (opened) return;
		opened = true;
		if (!reducedMotion) {
			var heartEl = document.querySelector ? document.querySelector(".cover-heart") : null;
			var bx = viewW / 2;
			var by = viewH * 0.35;
			if (heartEl) {
				var r = heartEl.getBoundingClientRect();
				bx = r.left + r.width / 2;
				by = r.top + r.height / 2;
			}
			triggerBurstAt(bx, by, [340, 350, 15, 30, 42], 25);
		}
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
     data-tint="name"        on a .scene — colour-grades the ambient glow
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

/* --- Moving between scenes --- */
function showHint() {
	clearTimeout(hintTimer);
	if (sceneIndex >= storyScenes.length - 1) {
		$("#hint").text("hold anywhere to send hearts");
	} else if (sceneIndex === 0) {
		$("#hint").text(isMobile ? "tap or swipe to continue" : "click or press space to continue");
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

/* One thump from the heart as a new chapter lands */
function thumpHeart() {
	if (reducedMotion || !$loveHeart) return;
	$loveHeart.removeClass("thump");
	/* Restart the animation even if a thump is already running */
	if ($loveHeart[0]) void $loveHeart[0].offsetWidth;
	$loveHeart.addClass("thump");
	setTimeout(function () {
		$loveHeart.removeClass("thump");
	}, 950);
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
	var tint = scene.getAttribute("data-tint") || "intro";
	resetScene(scene);
	$(scene).removeClass("leaving").addClass("active");
	$("#dots span").removeClass("on").eq(index).addClass("on");
	$("#progressFill").css("width", (storyScenes.length > 1 ? index / (storyScenes.length - 1) * 100 : 100) + "%");
	document.body.setAttribute("data-tint", tint);
	thumpHeart();

	// If the heart is already complete and the user goes back to a dated scene, show its date
	if (heartComplete) {
		var isFinaleScene = index >= storyScenes.length - 2;
		$("body").toggleClass("finished", isFinaleScene);
	}

	if (tint === "proposal") {
		triggerMilestoneShimmer([338, 348, 356, 20, 35]);
	} else if (tint === "wedding") {
		triggerMilestoneShimmer([28, 34, 40, 46, 350]);
	}

	setHeartDate(scene.getAttribute("data-day"), scene.getAttribute("data-year"));
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

	// Tapping a progress dot jumps directly to that chapter
	$("#dots span").each(function (idx) {
		$(this).click(function (e) {
			e.stopPropagation();
			if (!storyStarted) return;
			goToScene(idx);
		});
	});

	// Distinguish quick taps from long-press heart streams and horizontal swipes
	var gestureStartX = 0;
	var gestureStartY = 0;
	var gestureStartTime = 0;
	var suppressNextClick = false;
	var mainEl = document.getElementById("mainDiv");

	if (mainEl) {
		mainEl.addEventListener("touchstart", function (e) {
			if (!e.touches || !e.touches.length) return;
			gestureStartX = e.touches[0].clientX;
			gestureStartY = e.touches[0].clientY;
			gestureStartTime = Date.now();
		}, { passive: true });

		mainEl.addEventListener("touchend", function (e) {
			if (!storyStarted || !e.changedTouches || !e.changedTouches.length) return;
			var dx = e.changedTouches[0].clientX - gestureStartX;
			var dy = e.changedTouches[0].clientY - gestureStartY;
			var dt = Date.now() - gestureStartTime;

			// Horizontal swipe: left advances, right goes back a scene
			if (Math.abs(dx) > 42 && Math.abs(dx) > Math.abs(dy) * 1.3 && dt < 650) {
				suppressNextClick = true;
				if (dx < 0) {
					advanceStory();
				} else if (sceneBusy) {
					rushScene();
				} else if (sceneIndex > 0) {
					goToScene(sceneIndex - 1);
				}
				return;
			}

			// Long-press (holding to send hearts) should not advance the scene on release
			if (dt >= 280 || Math.abs(dx) > 20 || Math.abs(dy) > 20) {
				suppressNextClick = true;
			}
		});

		mainEl.addEventListener("mousedown", function (e) {
			gestureStartX = e.clientX;
			gestureStartY = e.clientY;
			gestureStartTime = Date.now();
		});

		mainEl.addEventListener("mouseup", function (e) {
			var dt = Date.now() - gestureStartTime;
			var dx = e.clientX - gestureStartX;
			var dy = e.clientY - gestureStartY;
			if (dt >= 280 || Math.abs(dx) > 20 || Math.abs(dy) > 20) {
				suppressNextClick = true;
			}
		});
	}

	// Anywhere on the page moves the story on (buttons and dots look after themselves)
	$("#mainDiv").click(function (e) {
		if (suppressNextClick) {
			suppressNextClick = false;
			return;
		}
		if ($(e.target).closest("button, a, #dots").length) return;
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

	/* The finale count-up owns the day number while it is running */
	if (!finaleCounting) {
		setText("elapseDays", String(days).replace(/\B(?=(\d{3})+$)/g, ","));
	}
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
function formatDays(days) {
	return String(days).replace(/\B(?=(\d{3})+$)/g, ",");
}

/* Roll the day count up from zero, then hand it back to timeElapse() */
function countUpDays() {
	if (typeof together === 'undefined' || reducedMotion) return;
	var target = Math.max(0, Math.floor((new Date().getTime() - together.getTime()) / 86400000));
	var token = ++finaleCountToken;
	var startTime = null;
	finaleCounting = true;
	setText("elapseDays", "0");
	function step(timestamp) {
		if (token !== finaleCountToken) return;
		if (!startTime) startTime = timestamp;
		var t = Math.min((timestamp - startTime) / 1800, 1);
		var eased = 1 - Math.pow(1 - t, 3);
		setText("elapseDays", formatDays(Math.round(target * eased)));
		if (t < 1) {
			requestAnimationFrame(step);
		} else {
			finaleCounting = false;
			timeElapse(together);
		}
	}
	requestAnimationFrame(step);
}

function showMessages() {
	adjustWordsPosition();
	// CSS takes it from here: the date gives way to the running count
	$("body").addClass("finished");
	countUpDays();
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

	var lastTouchTime = 0;

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

	document.addEventListener("mousedown", function (e) {
		if (Date.now() - lastTouchTime < 650) return;
		press(e);
	});
	document.addEventListener("mousemove", function (e) {
		if (Date.now() - lastTouchTime < 650) return;
		move(e);
	});
	document.addEventListener("mouseup", function () {
		if (Date.now() - lastTouchTime < 650) return;
		release();
	});
	document.addEventListener("touchstart", function (e) {
		lastTouchTime = Date.now();
		if (e.touches && e.touches[0]) press(e.touches[0]);
	}, { passive: true });
	document.addEventListener("touchmove", function (e) {
		lastTouchTime = Date.now();
		if (e.touches && e.touches[0]) move(e.touches[0]);
	}, { passive: true });
	document.addEventListener("touchend", function () {
		lastTouchTime = Date.now();
		release();
	});
	document.addEventListener("touchcancel", function () {
		lastTouchTime = Date.now();
		release();
	});

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
