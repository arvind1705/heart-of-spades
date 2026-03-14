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
		ctx.lineWidth = 1.2;
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
			this.garden.removeBloom(this);
		}
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
			Garden.randomInt(Garden.options.bloomRadius.min, Garden.options.bloomRadius.max),
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
	}
};

Garden.options = {
	petalCount: { min: 8, max: 15 },
	petalStretch: { min: 0.1, max: 3 },
	growFactor: { min: 0.1, max: 1 },
	bloomRadius: { min: 8, max: 12 },
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
	{ r: [180, 230], g: [80, 130], b: [100, 150], o: 0.18 },   // rose pink
	{ r: [200, 245], g: [120, 170], b: [100, 140], o: 0.15 },   // peach / rose gold
	{ r: [190, 240], g: [60, 100], b: [90, 140], o: 0.16 },     // deep rose
	{ r: [210, 255], g: [140, 190], b: [130, 170], o: 0.12 },   // soft blush
	{ r: [170, 220], g: [90, 130], b: [120, 170], o: 0.14 },    // mauve
];

Garden.randomRomanticColor = function () {
	var p = Garden.romanticPalette[Garden.randomInt(0, Garden.romanticPalette.length - 1)];
	var r = Garden.randomInt(p.r[0], p.r[1]);
	var g = Garden.randomInt(p.g[0], p.g[1]);
	var b = Garden.randomInt(p.b[0], p.b[1]);
	return Garden.rgba(r, g, b, p.o);
};

Garden.randomGlowColor = function () {
	var glows = [
		"rgba(232, 168, 124, 0.3)",
		"rgba(212, 175, 140, 0.25)",
		"rgba(207, 102, 121, 0.3)",
		"rgba(200, 140, 160, 0.25)",
		"rgba(230, 180, 150, 0.2)"
	];
	return glows[Garden.randomInt(0, glows.length - 1)];
};

Garden.randomrgba = function (i, n, h, m, l, d, k) {
	var c = Math.round(Garden.random(i, n));
	var f = Math.round(Garden.random(h, m));
	var j = Math.round(Garden.random(l, d));
	return Garden.rgba(c, f, j, k);
};
