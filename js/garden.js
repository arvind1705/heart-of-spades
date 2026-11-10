/* ============================================
   Garden.js — Bloom Animation Engine
   Enhanced with glow effects for dark theme
   ============================================ */

function Vector(a, b) {
	this.x = a;
	this.y = b;
}

Vector.prototype = {
	rotate: function (b) {
		var a = this.x;
		var c = this.y;
		this.x = Math.cos(b) * a - Math.sin(b) * c;
		this.y = Math.sin(b) * a + Math.cos(b) * c;
		return this;
	},
	mult: function (a) {
		this.x *= a;
		this.y *= a;
		return this;
	},
	clone: function () {
		return new Vector(this.x, this.y);
	},
	length: function () {
		return Math.sqrt(this.x * this.x + this.y * this.y);
	},
	subtract: function (a) {
		this.x -= a.x;
		this.y -= a.y;
		return this;
	},
	set: function (a, b) {
		this.x = a;
		this.y = b;
		return this;
	}
};

function Petal(a, f, b, e, c, d) {
	this.stretchA = a;
	this.stretchB = f;
	this.startAngle = b;
	this.angle = e;
	this.bloom = d;
	this.growFactor = c;
	this.r = 1;
	this.isfinished = false;
}

Petal.prototype = {
	draw: function () {
		var ctx = this.bloom.garden.ctx;
		var e, d, c, b;
		e = new Vector(0, this.r).rotate(Garden.degrad(this.startAngle));
		d = e.clone().rotate(Garden.degrad(this.angle));
		c = e.clone().mult(this.stretchA);
		b = d.clone().mult(this.stretchB);

		ctx.strokeStyle = this.bloom.c;
		ctx.lineWidth = Garden.options.lineWidth;
		ctx.shadowColor = this.bloom.glowColor || this.bloom.c;
		/* Reduce GPU-heavy shadowBlur on mobile */
		ctx.shadowBlur = (typeof isMobile !== 'undefined' && isMobile) ? 2 : 6;
		ctx.beginPath();
		ctx.moveTo(e.x, e.y);
		ctx.bezierCurveTo(c.x, c.y, b.x, b.y, d.x, d.y);
		ctx.stroke();
		ctx.shadowBlur = 0;
	},
	render: function () {
		if (this.r <= this.bloom.r) {
			this.r += this.growFactor;
			this.draw();
		} else {
			this.isfinished = true;
		}
	}
};

function Bloom(e, d, f, a, b, glowColor) {
	this.p = e;
	this.r = d;
	this.c = f;
	this.pc = a;
	this.petals = [];
	this.garden = b;
	this.glowColor = glowColor || f;
	this.init();
	this.garden.addBloom(this);
}

Bloom.prototype = {
	draw: function () {
		var c, b = true;
		this.garden.ctx.save();
		this.garden.ctx.translate(this.p.x, this.p.y);
		for (var a = 0; a < this.petals.length; a++) {
			c = this.petals[a];
			c.render();
			b *= c.isfinished;
		}
		this.garden.ctx.restore();
		if (b == true) {
			this.drawCentre();
			this.garden.removeBloom(this);
		}
	},
	/* One soft glow at the heart of each finished bloom */
	drawCentre: function () {
		var ctx = this.garden.ctx;
		ctx.save();
		ctx.translate(this.p.x, this.p.y);
		ctx.beginPath();
		ctx.arc(0, 0, Math.max(1.2, this.r * 0.16), 0, Garden.circle);
		ctx.fillStyle = this.glowColor;
		ctx.shadowColor = this.glowColor;
		ctx.shadowBlur = (typeof isMobile !== 'undefined' && isMobile) ? 3 : 8;
		ctx.fill();
		ctx.restore();
	},
	init: function () {
		var c = 360 / this.pc;
		var b = Garden.randomInt(0, 90);
		for (var a = 0; a < this.pc; a++) {
			this.petals.push(new Petal(
				Garden.random(Garden.options.petalStretch.min, Garden.options.petalStretch.max),
				Garden.random(Garden.options.petalStretch.min, Garden.options.petalStretch.max),
				b + a * c,
				c,
				Garden.random(Garden.options.growFactor.min, Garden.options.growFactor.max),
				this
			));
		}
	}
};

function Garden(a, b) {
	this.blooms = [];
	this.element = b;
	this.ctx = a;
}

Garden.prototype = {
	render: function () {
		for (var a = 0; a < this.blooms.length; a++) {
			this.blooms[a].draw();
		}
	},
	addBloom: function (a) {
		this.blooms.push(a);
	},
	removeBloom: function (a) {
		var d;
		for (var c = 0; c < this.blooms.length; c++) {
			d = this.blooms[c];
			if (d === a) {
				this.blooms.splice(c, 1);
				return this;
			}
		}
	},
	createRandomBloom: function (a, b) {
		var color = Garden.randomRomanticColor();
		var glowColor = Garden.randomGlowColor();
		this.createBloom(
			a, b,
			Garden.random(Garden.options.bloomRadius.min, Garden.options.bloomRadius.max),
			color,
			Garden.randomInt(Garden.options.petalCount.min, Garden.options.petalCount.max),
			glowColor
		);
	},
	createBloom: function (a, f, d, e, b, glowColor) {
		new Bloom(new Vector(a, f), d, e, b, this, glowColor);
	},
	clear: function () {
		this.blooms = [];
		this.ctx.clearRect(0, 0, this.element.width, this.element.height);
	},
	/* Keep blooms that are still growing in place when the canvas is resized */
	rescale: function (k) {
		var bloom;
		for (var a = 0; a < this.blooms.length; a++) {
			bloom = this.blooms[a];
			bloom.p.x *= k;
			bloom.p.y *= k;
			bloom.r *= k;
			for (var c = 0; c < bloom.petals.length; c++) {
				bloom.petals[c].r *= k;
			}
		}
	}
};

Garden.options = {
	petalCount: { min: 8, max: 15 },
	petalStretch: { min: 0.1, max: 3 },
	growFactor: { min: 0.1, max: 1 },
	bloomRadius: { min: 8, max: 12 },
	lineWidth: 1.2,
	density: 10,
	growSpeed: 1000 / 60,
	color: {
		rmin: 160, rmax: 255,
		gmin: 50, gmax: 140,
		bmin: 70, bmax: 160,
		opacity: 0.15
	},
	tanAngle: 60
};

Garden.random = function (b, a) {
	return Math.random() * (a - b) + b;
};

Garden.randomInt = function (b, a) {
	return Math.floor(Math.random() * (a - b + 1)) + b;
};

Garden.circle = 2 * Math.PI;

Garden.degrad = function (a) {
	return Garden.circle / 360 * a;
};

Garden.raddeg = function (a) {
	return a / Garden.circle * 360;
};

Garden.rgba = function (f, e, c, d) {
	return "rgba(" + f + "," + e + "," + c + "," + d + ")";
};

/* Enhanced color palette for dark romantic theme */
Garden.romanticPalette = [
	{ r: [180, 230], g: [80, 130], b: [100, 150], o: 0.30 },   // rose pink
	{ r: [200, 245], g: [120, 170], b: [100, 140], o: 0.25 },   // peach / rose gold
	{ r: [190, 240], g: [60, 100], b: [90, 140], o: 0.28 },     // deep rose
	{ r: [210, 255], g: [140, 190], b: [130, 170], o: 0.20 },   // soft blush
	{ r: [170, 220], g: [90, 130], b: [120, 170], o: 0.24 },    // mauve
	{ r: [215, 255], g: [165, 205], b: [95, 135], o: 0.22 },    // warm gold
];

/* Bloom palettes per theme (mirrors body[data-theme] in default.css) */
Garden.theme = "rose";

Garden.palettes = {
	rose: Garden.romanticPalette,
	champagne: [
		{ r: [225, 255], g: [170, 205], b: [110, 150], o: 0.28 },   // champagne gold
		{ r: [210, 245], g: [130, 170], b: [95, 130], o: 0.26 },     // peach coral
		{ r: [235, 255], g: [190, 220], b: [140, 175], o: 0.22 },    // cream blush
		{ r: [200, 240], g: [110, 150], b: [90, 125], o: 0.27 },     // coral
		{ r: [220, 250], g: [160, 195], b: [105, 140], o: 0.24 }     // apricot
	]
};

Garden.glowPalettes = {
	rose: [
		"rgba(232, 168, 124, 0.45)",
		"rgba(212, 175, 140, 0.38)",
		"rgba(207, 102, 121, 0.45)",
		"rgba(200, 140, 160, 0.38)",
		"rgba(230, 180, 150, 0.32)"
	],
	champagne: [
		"rgba(247, 227, 184, 0.45)",
		"rgba(244, 196, 120, 0.42)",
		"rgba(232, 138, 106, 0.42)",
		"rgba(240, 178, 132, 0.38)",
		"rgba(250, 214, 150, 0.34)"
	]
};

Garden.randomRomanticColor = function () {
	var palette = Garden.palettes[Garden.theme] || Garden.romanticPalette;
	var p = palette[Garden.randomInt(0, palette.length - 1)];
	var r = Garden.randomInt(p.r[0], p.r[1]);
	var g = Garden.randomInt(p.g[0], p.g[1]);
	var b = Garden.randomInt(p.b[0], p.b[1]);
	return Garden.rgba(r, g, b, p.o);
};

Garden.randomGlowColor = function () {
	var glows = Garden.glowPalettes[Garden.theme] || Garden.glowPalettes.rose;
	return glows[Garden.randomInt(0, glows.length - 1)];
};

Garden.randomrgba = function (i, n, h, m, l, d, k) {
	var c = Math.round(Garden.random(i, n));
	var f = Math.round(Garden.random(h, m));
	var j = Math.round(Garden.random(l, d));
	return Garden.rgba(c, f, j, k);
};
