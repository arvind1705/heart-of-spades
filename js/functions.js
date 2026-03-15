/* ============================================
   Functions.js — App Logic
   Enhanced with smooth animations & particles
   ============================================ */

var $window = $(window), gardenCtx, gardenCanvas, $garden, garden;

/* --- Mobile Detection Helper --- */
var isMobile = (function() {
	return window.innerWidth <= 768 || ('ontouchstart' in window);
})();

/* --- Floating Particle / Sparkle System --- */
var particleCanvas, particleCtx, particles = [];
var particleBurstActive = false;
var particleLastTime = 0;

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

/* --- Shared Name-Reveal Particle Burst ---
   hueOptions : array of hue values for the first wave
   shimmerHueBase : base hue for the shimmer wave
*/
function triggerRevealBurst(elementId, hueOptions, shimmerHueBase) {
	particleBurstActive = true;

	// Origin: centre of the reveal element if available, else screen centre
	var originX = window.innerWidth / 2;
	var originY = window.innerHeight / 2;
	if (elementId) {
		var el = document.getElementById(elementId);
		if (el) {
			var rect = el.getBoundingClientRect();
			originX = rect.left + rect.width / 2;
			originY = rect.top + rect.height / 2 + window.pageYOffset;
		}
	}

	var burstCount = isMobile ? 40 : 80;
	for (var i = 0; i < burstCount; i++) {
		var angle = (Math.PI * 2 / burstCount) * i + (Math.random() - 0.5) * 0.4;
		var speed = Math.random() * 3 + 1.5;
		var hue = hueOptions[Math.floor(Math.random() * hueOptions.length)] + Math.random() * 15;

		particles.push(createParticle({
			x: originX + (Math.random() - 0.5) * 60,
			y: originY + (Math.random() - 0.5) * 60,
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
	var ox = originX, oy = originY;
	setTimeout(function () {
		for (var i = 0; i < shimmerCount; i++) {
			var angle = Math.random() * Math.PI * 2;
			var speed = Math.random() * 1.5 + 0.5;
			particles.push(createParticle({
				x: ox + (Math.random() - 0.5) * 200,
				y: oy + (Math.random() - 0.5) * 200,
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

function triggerDaivikBurst() {
	// Warm: pinks, reds, golds
	triggerRevealBurst('daivikReveal', [340, 350, 0, 10, 20, 30, 40, 50], 15);
}

function triggerBabyBurst() {
	// Lavender / mauve — bridges rose palette and stays distinct from Daivik gold
	triggerRevealBurst('babyReveal', [280, 290, 300, 310, 320, 330], 290);
}

/* --- Finale shimmer: gentle gold-rose shower across the full screen --- */
function triggerFinaleShimmer() {
	var shimmerCount = isMobile ? 30 : 70;
	for (var i = 0; i < shimmerCount; i++) {
		setTimeout(function() {
			var hueOpts = [340, 350, 0, 20, 40, 300, 310];
			var hue = hueOpts[Math.floor(Math.random() * hueOpts.length)];
			particles.push(createParticle({
				x: Math.random() * window.innerWidth,
				y: Math.random() * window.innerHeight,
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

function animateParticles(timestamp) {
	if (!particleCtx) return;

	var delta = particleLastTime ? Math.min(timestamp - particleLastTime, 64) : 16;
	particleLastTime = timestamp;

	particleCtx.clearRect(0, 0, particleCanvas.width, particleCanvas.height);

	for (var i = particles.length - 1; i >= 0; i--) {
		var p = particles[i];

		p.x += p.speedX;
		p.y += p.speedY;

		// Burst particles decelerate and fade using real delta time
		if (p.isBurst) {
			p.speedX *= 0.985;
			p.speedY *= 0.985;
			p.life -= delta;
			p.opacity += p.opacitySpeed * (delta / 16);
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

	// Exact bounding box of the parametric heart curve
	// (b = c/PI, x = 16*sin^3(b), y = -(13cos(b)-5cos(2b)-2cos(3b)-cos(4b)))
	// X is symmetric: [-16, 16], Y range: [-11.9233, 17.0]
	var normHalfW = 16;          // half-width of normalised heart
	var normMinY  = -11.9233;    // top of normalised heart
	var normMaxY  =  17.0;       // bottom of normalised heart
	var normH     = normMaxY - normMinY; // 28.9233

	var pad = Math.min(w, h) * 0.04; // ~4% of the shorter side as margin

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

	// Use rAF instead of setInterval so render syncs with display refresh
	// and pauses automatically when the tab is backgrounded
	function gardenRenderLoop() {
		garden.render();
		requestAnimationFrame(gardenRenderLoop);
	}
	requestAnimationFrame(gardenRenderLoop);
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
		// Re-measure the heart panel and recalc metrics
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

/* --- Typewriter with pause support, milestone detection, skip & replay --- */
(function (a) {
	a.fn.typewriter = function () {
		this.each(function () {
			var d = a(this);
			var originalHTML = d.html();
			var b = 0;
			d.html("");

			var daivikTriggered = false;
			var babyTriggered = false;
			var whileTrueTriggered = false;
			var proposeTriggered = false;
			var marryTriggered = false;
			var heartAnimStarted = false;
			var speed = 30;
			var pauseUntil = 0;
			var intervalId = null;
			var finished = false;

			/* --- Skip: jump to end instantly --- */
			function skipToEnd() {
				if (finished) return;
				if (intervalId) clearInterval(intervalId);
				finished = true;
				d.html(originalHTML);
				// Fire all milestone effects that haven't triggered yet
				if (!daivikTriggered) {
					triggerDaivikBurst();
					var elD = document.getElementById('daivikReveal');
					if (elD) elD.classList.add('revealed');
				}
				if (!babyTriggered) {
					triggerBabyBurst();
					var elB = document.getElementById('babyReveal');
					if (elB) elB.classList.add('revealed');
				}
				triggerFinaleShimmer();
				if (!heartAnimStarted) {
					heartAnimStarted = true;
					setTimeout(startHeartAnimation, 800);
				}
				showSkipReplayBtn('replay');
			}

			/* --- Replay: reset and retype --- */
			function replay() {
				b = 0;
				finished = false;
				daivikTriggered = false;
				babyTriggered = false;
				whileTrueTriggered = false;
				proposeTriggered = false;
				marryTriggered = false;
				heartAnimStarted = false;
				pauseUntil = 0;
				garden.clear();
				$("#messages").css({ display: 'none', opacity: 0 });
				$("#loveu").css({ display: 'none', opacity: 0 });
				d.html("");
				showSkipReplayBtn('skip');
				intervalId = setInterval(tick, speed);
			}

			function showSkipReplayBtn(mode) {
				var btn = document.getElementById('skipBtn');
				if (!btn) return;
				if (mode === 'skip') {
					btn.innerHTML = '&#8595; Skip';
					btn.onclick = skipToEnd;
					btn.style.display = 'block';
				} else {
					btn.innerHTML = '&#8635; Replay';
					btn.onclick = replay;
					btn.style.display = 'block';
				}
			}

			// Wire the skip button immediately
			showSkipReplayBtn('skip');

			/* --- Scroll throttle --- */
			var scrollPending = false;
			function scheduleScroll(el) {
				if (scrollPending) return;
				scrollPending = true;
				requestAnimationFrame(function() {
					scrollPending = false;
					if (el.scrollHeight > el.clientHeight) {
						el.scrollTop = el.scrollHeight - el.clientHeight;
					}
				});
			}

			function tick() {
				var c = originalHTML;
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

				// Throttled auto-scroll
				scheduleScroll(d[0]);

				// while True block — pause to let the moment breathe
				if (!whileTrueTriggered && currentHTML.indexOf('id="whileTrue"') !== -1 &&
					b > c.indexOf('whileTrue') + 10) {
					whileTrueTriggered = true;
					pauseUntil = now + 900;
				}

				// Proposal — pause
				if (!proposeTriggered && currentHTML.indexOf('id="proposeReveal"') !== -1 &&
					b > c.indexOf('proposeReveal') + 10) {
					proposeTriggered = true;
					pauseUntil = now + 1000;
				}

				// Wedding — pause
				if (!marryTriggered && currentHTML.indexOf('id="marryReveal"') !== -1 &&
					b > c.indexOf('marryReveal') + 10) {
					marryTriggered = true;
					pauseUntil = now + 1000;
				}

				// Daivik reveal
				if (!daivikTriggered && currentHTML.indexOf('id="daivikReveal"') !== -1 &&
					currentHTML.indexOf('Daivik') !== -1 &&
					b > c.indexOf('Daivik') + 5) {
					daivikTriggered = true;
					triggerDaivikBurst();
					setTimeout(function() {
						var el = document.getElementById('daivikReveal');
						if (el) el.classList.add('revealed');
					}, 100);
					pauseUntil = now + 1200;
				}

				// Baby #2 reveal
				if (!babyTriggered && currentHTML.indexOf('id="babyReveal"') !== -1 &&
					currentHTML.indexOf('Baby #2') !== -1 &&
					b > c.indexOf('Baby #2') + 5) {
					babyTriggered = true;
					triggerBabyBurst();
					setTimeout(function() {
						var el = document.getElementById('babyReveal');
						if (el) el.classList.add('revealed');
					}, 100);
					pauseUntil = now + 1200;
				}

				if (b >= c.length) {
					clearInterval(intervalId);
					finished = true;
					// Remove cursor
					setTimeout(function () {
						d.find('.cursor').fadeOut(600);
					}, 1500);
					// Finale shimmer
					setTimeout(triggerFinaleShimmer, 600);
					// Start heart animation
					if (!heartAnimStarted) {
						heartAnimStarted = true;
						setTimeout(startHeartAnimation, 1500);
					}
					showSkipReplayBtn('replay');
				}
			}

			intervalId = setInterval(tick, speed);
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

	var a = '<span class="digit heartbeat">' + g + '</span><span class="time-label">days</span>'
		+ '<span class="digit">' + b + '</span><span class="time-label">hrs</span>'
		+ '<span class="digit">' + d + '</span><span class="time-label">min</span>'
		+ '<span class="digit heartbeat">' + f + '</span><span class="time-label">sec</span>';
	$("#elapseClock").html(a);
}

/* --- Enhanced Message Reveal --- */
function showMessages() {
	adjustWordsPosition();
	$("#messages").css("display", "block").animate({ opacity: 1 }, 2500, function () {
		showLoveU();
	});
}

function adjustWordsPosition() {
	// no-op: #words is in normal document flow below the heart
}

function showLoveU() {
	$("#loveu").css("display", "block").animate({ opacity: 1 }, 3000);
}
