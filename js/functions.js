/* ============================================
   Functions.js — App Logic
   Enhanced with smooth animations & particles
   ============================================ */

var $window = $(window), gardenCtx, gardenCanvas, $garden, garden;
var clientWidth = $(window).width();
var clientHeight = $(window).height();

/* --- Mobile Detection Helper --- */
var isMobile = (function() {
	return window.innerWidth <= 768 || ('ontouchstart' in window);
})();

/* --- Floating Particle / Sparkle System --- */
var particleCanvas, particleCtx, particles = [];
var particleBurstActive = false;

function initParticles() {
	particleCanvas = document.getElementById('particleCanvas');
	if (!particleCanvas) return;
	particleCtx = particleCanvas.getContext('2d');
	resizeParticleCanvas();
	window.addEventListener('resize', resizeParticleCanvas);

	// Create initial particles — fewer on mobile for performance
	var maxParticles = isMobile ? 50 : 120;
	var count = Math.min(Math.floor(window.innerWidth * window.innerHeight / 8000), maxParticles);
	for (var i = 0; i < count; i++) {
		particles.push(createParticle());
	}
	requestAnimationFrame(animateParticles);
}

function resizeParticleCanvas() {
	if (!particleCanvas) return;
	particleCanvas.width = window.innerWidth;
	particleCanvas.height = window.innerHeight;
}

function createParticle(options) {
	var types = ['circle', 'star'];
	var defaults = {
		x: Math.random() * window.innerWidth,
		y: Math.random() * window.innerHeight,
		size: Math.random() * 2.5 + 0.5,
		speedX: (Math.random() - 0.5) * 0.3,
		speedY: -Math.random() * 0.4 - 0.1,
		opacity: Math.random() * 0.5 + 0.1,
		opacitySpeed: (Math.random() - 0.5) * 0.008,
		type: types[Math.floor(Math.random() * types.length)],
		hue: Math.random() * 40 + 15, // warm gold range (15-55)
		life: -1, // -1 = infinite
		isBurst: false
	};
	if (options) {
		for (var key in options) {
			defaults[key] = options[key];
		}
	}
	return defaults;
}

/* --- Daivik Particle Burst --- */
function triggerDaivikBurst() {
	particleBurstActive = true;
	var centerX = window.innerWidth / 2;
	var centerY = window.innerHeight / 2;
	var burstCount = isMobile ? 40 : 80;

	for (var i = 0; i < burstCount; i++) {
		var angle = (Math.PI * 2 / burstCount) * i + (Math.random() - 0.5) * 0.4;
		var speed = Math.random() * 3 + 1.5;
		var hueOptions = [340, 350, 0, 10, 20, 30, 40, 50]; // pinks, reds, golds
		var hue = hueOptions[Math.floor(Math.random() * hueOptions.length)] + Math.random() * 15;

		particles.push(createParticle({
			x: centerX + (Math.random() - 0.5) * 60,
			y: centerY + (Math.random() - 0.5) * 60,
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
				x: centerX + (Math.random() - 0.5) * 200,
				y: centerY + (Math.random() - 0.5) * 200,
				size: Math.random() * 2 + 0.8,
				speedX: Math.cos(angle) * speed * 0.3,
				speedY: -Math.random() * 0.8 - 0.3,
				opacity: 0.6 + Math.random() * 0.3,
				opacitySpeed: -0.004 - Math.random() * 0.003,
				type: 'star',
				hue: Math.random() * 50 + 20,
				life: 4000 + Math.random() * 2000,
				isBurst: true
			}));
		}
	}, 800);
}

function animateParticles() {
	if (!particleCtx) return;
	particleCtx.clearRect(0, 0, particleCanvas.width, particleCanvas.height);

	for (var i = particles.length - 1; i >= 0; i--) {
		var p = particles[i];

		p.x += p.speedX;
		p.y += p.speedY;

		// Burst particles decelerate and fade
		if (p.isBurst) {
			p.speedX *= 0.985;
			p.speedY *= 0.985;
			p.life -= 16; // approx 1 frame at 60fps
			p.opacity += p.opacitySpeed;
			if (p.life <= 0 || p.opacity <= 0) {
				particles.splice(i, 1);
				continue;
			}
		} else {
			p.opacity += p.opacitySpeed;
			if (p.opacity <= 0.05 || p.opacity >= 0.6) {
				p.opacitySpeed *= -1;
			}
			// Wrap around
			if (p.y < -10) { p.y = particleCanvas.height + 10; p.x = Math.random() * particleCanvas.width; }
			if (p.x < -10) p.x = particleCanvas.width + 10;
			if (p.x > particleCanvas.width + 10) p.x = -10;
		}

		// Draw
		particleCtx.save();
		particleCtx.globalAlpha = Math.max(0, Math.min(1, p.opacity));

		if (p.type === 'star') {
			drawStar(particleCtx, p.x, p.y, p.size, p.hue);
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

/* --- Main Initialization --- */

/* Dynamic heart scale factors — computed from actual canvas size */
var heartScaleX, heartScaleY, offsetX, offsetY;

function computeHeartMetrics() {
	var w = gardenCanvas.width;
	var h = gardenCanvas.height;
	// Original design: canvas 620x580, scaleX=19.5, scaleY=20, offsetY shift=-55
	// Scale proportionally from that reference
	heartScaleX = w / 620 * 19.5;
	heartScaleY = h / 580 * 20;
	offsetX = w / 2;
	offsetY = h / 2 - (55 * h / 580);
}

function sizeCanvas() {
	var $lh = $("#loveHeart");
	var w = $lh.width();
	var h = $lh.height();
	gardenCanvas.width = w;
	gardenCanvas.height = h;
	computeHeartMetrics();
}

$(function () {
	// Init particles
	initParticles();

	$loveHeart = $("#loveHeart");
	$garden = $("#garden");
	gardenCanvas = $garden[0];
	gardenCtx = gardenCanvas.getContext("2d");
	gardenCtx.globalCompositeOperation = "lighter";
	garden = new Garden(gardenCtx, gardenCanvas);

	// Size canvas to match the CSS-laid-out container
	sizeCanvas();

	setInterval(function () {
		garden.render();
	}, Garden.options.growSpeed);
});

/* Replace page-reload-on-resize with proper recalculation */
var resizeTimer;
$(window).resize(function () {
	clearTimeout(resizeTimer);
	resizeTimer = setTimeout(function() {
		// Update mobile detection
		isMobile = window.innerWidth <= 768 || ('ontouchstart' in window);
		// Resize particle canvas
		resizeParticleCanvas();
		// Re-measure the heart panel and recalc metrics (canvas won't re-render
		// existing blooms at new positions, but new blooms will be correct;
		// also adjustWordsPosition will use correct values)
		if (gardenCanvas) {
			sizeCanvas();
		}
	}, 250);
});

function getHeartPoint(c) {
	var b = c / Math.PI;
	var a = heartScaleX * (16 * Math.pow(Math.sin(b), 3));
	var d = -heartScaleY * (13 * Math.cos(b) - 5 * Math.cos(2 * b) - 2 * Math.cos(3 * b) - Math.cos(4 * b));
	return new Array(offsetX + a, offsetY + d);
}

function startHeartAnimation() {
	var c = 50;
	var d = 10;
	var b = new Array();
	var a = setInterval(function () {
		var h = getHeartPoint(d);
		var e = true;
		for (var f = 0; f < b.length; f++) {
			var g = b[f];
			var j = Math.sqrt(Math.pow(g[0] - h[0], 2) + Math.pow(g[1] - h[1], 2));
			if (j < Garden.options.bloomRadius.max * 1.3) {
				e = false;
				break;
			}
		}
		if (e) {
			b.push(h);
			garden.createRandomBloom(h[0], h[1]);
		}
		if (d >= 30) {
			clearInterval(a);
			showMessages();
		} else {
			d += 0.2;
		}
	}, c);
}

/* --- Enhanced Typewriter with pause support & Daivik detection --- */
(function (a) {
	a.fn.typewriter = function () {
		this.each(function () {
			var d = a(this), c = d.html(), b = 0;
			var totalVisibleChars = c.replace(/<[^>]*>/g, '').length;
			d.html("");

			var daivikTriggered = false;
			var heartAnimStarted = false;
			var speed = 30;
			var pauseUntil = 0;

			var e = setInterval(function () {
				var now = Date.now();
				if (now < pauseUntil) return;

				var f = c.substr(b, 1);
				if (f == "<") {
					b = c.indexOf(">", b) + 1;
				} else {
					b++;
				}

				var currentHTML = c.substring(0, b);
				d.html(currentHTML + '<span class="cursor"></span>');

				// Auto-scroll to keep cursor visible
				var codeEl = d[0];
				if (codeEl.scrollHeight > codeEl.clientHeight) {
					codeEl.scrollTop = codeEl.scrollHeight - codeEl.clientHeight;
				}

				// Detect when Daivik's name appears
				if (!daivikTriggered && currentHTML.indexOf('id="daivikReveal"') !== -1 &&
					currentHTML.indexOf('Daivik') !== -1 &&
					b > c.indexOf('Daivik') + 5) {
					daivikTriggered = true;
					// Trigger the burst effect
					triggerDaivikBurst();
					// Add glow class to the name
					setTimeout(function() {
						var el = document.getElementById('daivikReveal');
						if (el) el.classList.add('revealed');
					}, 100);
					// Pause briefly to let the moment breathe
					pauseUntil = now + 1200;
				}

				if (b >= c.length) {
					clearInterval(e);
					// Remove cursor
					setTimeout(function () {
						d.find('.cursor').fadeOut(600);
					}, 1500);
					// Start heart animation after typing finishes
					if (!heartAnimStarted) {
						heartAnimStarted = true;
						setTimeout(function() {
							startHeartAnimation();
						}, 1500);
					}
				}
			}, speed);
		});
		return this;
	};
})(jQuery);

/* --- Enhanced Time Elapsed --- */
function timeElapse(c) {
	var e = Date();
	var f = (Date.parse(e) - Date.parse(c)) / 1000;
	var g = Math.floor(f / (3600 * 24));
	f = f % (3600 * 24);
	var b = Math.floor(f / 3600);
	if (b < 10) b = "0" + b;
	f = f % 3600;
	var d = Math.floor(f / 60);
	if (d < 10) d = "0" + d;
	f = f % 60;
	if (f < 10) f = "0" + f;

	var a = '<span class="digit">' + g + '</span><span class="time-label">days</span>'
		+ '<span class="digit">' + b + '</span><span class="time-label">hrs</span>'
		+ '<span class="digit">' + d + '</span><span class="time-label">min</span>'
		+ '<span class="digit">' + f + '</span><span class="time-label">sec</span>';
	$("#elapseClock").html(a);
}

/* --- Enhanced Message Reveal --- */
function showMessages() {
	adjustWordsPosition();
	$("#messages").css("display", "block").animate({ opacity: 1 }, 5000, function () {
		showLoveU();
	});
}

function adjustWordsPosition() {
	var $gardenEl = $("#garden");
	var $words = $("#words");
	var canvasW = $gardenEl.width();
	var canvasH = $gardenEl.height();
	// Position text centered in the heart — proportional to canvas size
	// Original: canvas 620x580, top offset +195, left offset +55
	var topRatio = 195 / 580;
	var leftRatio = 55 / 620;
	$words.css("position", "absolute");
	$words.css("top", $gardenEl.position().top + canvasH * topRatio);
	$words.css("left", $gardenEl.position().left + canvasW * leftRatio);
}

function adjustCodePosition() {
	// No longer needed — CSS flexbox handles vertical alignment
}

function showLoveU() {
	$("#loveu").css("display", "block").animate({ opacity: 1 }, 3000);
}
