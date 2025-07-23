// API Script

var CHAR_NAME = '';

// Godly Audio Script
function aud(s:string) {
    AudioClip.play(self.getResource().getContent(s));
}

// Creates sprites and assigns the given animation
function createSprite(anim:string) {
    var newSprite = Sprite.create(self.getResource().getContent(CHAR_NAME));
    newSprite.currentAnimation = anim;
    return newSprite;
}

// Sprites
var ragingBackground = createSprite('black_background');


var bg = createSprite('black_background');

// Super Bar Related Variables

// Bar Holder Sprite
var superBar = createSprite('super_bar');

// Gauge Sprite
var superGaugeSprite = createSprite('super_gauge');
// Maximum Sprite
var maximumSprite = createSprite('maximum');

// Tracks Individual Super Gauge
var superGauge = 1;
// Tracks Animation of Super Gauge
var superGaugeVisual = 1;
// Determines Animation Interval
var superGaugeAnim = 0;
// Shader for Super After Images
var superShader = new RgbaColorShader();
// Tracks level
var level = 1;
// Maximum Tracker
var maximumLevel = false;
// Tracking the Anim Timer
var animTimer = -1;
// Listen for an attack press
var attackListen = true;
// Current Attack Button Anim
var attackAnim = null;
// For Tracking Whether the Attack Landed or not
var attackAnimLanded = false;
// Check Whiff
var checkWhiff = false;
// Holds Transistion States for Checking if a move whiffed
var transitionStates = [2,19,23];
// Creates a Map of Animations and the value to add to bar
var onHitAdd = new StringMap();
onHitAdd.set("aerial_neutral", 6);
onHitAdd.set("aerial_down", 8);
onHitAdd.set("aerial_forward", 6);
onHitAdd.set("aerial_up", 6);
onHitAdd.set("aerial_back", 8);
onHitAdd.set("jab1", 2);
onHitAdd.set("jab2", 2);
onHitAdd.set("jab3", 5);
onHitAdd.set("tilt_forward", 5);
onHitAdd.set("tilt_up", 6);
onHitAdd.set("tilt_down", 6);
onHitAdd.set("strong_forward_in", 8);
onHitAdd.set("strong_up_in", 6);
onHitAdd.set("strong_down_in", 8);
onHitAdd.set("dash_attack", 6);
onHitAdd.set("special_up", 5);
onHitAdd.set("special_up_air", 5);
onHitAdd.set("special_side", 8);
onHitAdd.set("special_down", 4);
onHitAdd.set("special_down_air", 4);

// Creates a Map of Animations and the value to add to bar when the move is whiffed
var onWhiffAdd = new StringMap();
onWhiffAdd.set("aerial_neutral", 3);
onWhiffAdd.set("aerial_down", 4);
onWhiffAdd.set("aerial_forward", 3);
onWhiffAdd.set("aerial_up", 3);
onWhiffAdd.set("aerial_back", 4);
onWhiffAdd.set("jab1", 1);
onWhiffAdd.set("tilt_forward", 2);
onWhiffAdd.set("tilt_up", 3);
onWhiffAdd.set("tilt_down", 4);
onWhiffAdd.set("strong_forward_in", 5);
onWhiffAdd.set("strong_up_in", 6);
onWhiffAdd.set("strong_down_in", 6);
onWhiffAdd.set("dash_attack", 5);

function initialize(){
    // Event Listener For Adding Bar
    self.addEventListener(GameObjectEvent.HIT_DEALT, onHitBar, {persistent: true});
    self.addEventListener(GameObjectEvent.HIT_DEALT, specialCancel, {persistent: true});
    self.addEventListener(GameObjectEvent.LAND, onLandBar, {persistent: true});

    // Adds the Super Bar Sprites to the Characters Damage Counter
    self.getDamageCounterContainer().y = -5;
    self.getDamageCounterContainer().addChild(superBar);
    self.getDamageCounterContainer().addChild(superGaugeSprite);
}

function specialCancel() {
    var curAnim = self.getAnimation();
    if (curAnim.split('_')[0] != 'special') {
        Common.onButtonsPressed(Buttons.SPECIAL, function () {
            self.forceStartHitstop(0);
            if (self.getHeldControls().UP) {
                self.toState(CState.SPECIAL_UP);
            }
            else if (self.getHeldControls().DOWN) {
                self.toState(CState.SPECIAL_DOWN);
            }
            else if (self.getHeldControls().LEFT || self.getHeldControls().RIGHT) {
                self.toState(CState.SPECIAL_SIDE);
            }
            else self.toState(CState.SPECIAL_NEUTRAL);
        });
    }
    
}


// Super Related Functions

// Function to Add Bar to the Super Gauge
function addToGuage(addition) {
    if (maximumLevel == false) {
        superGauge += addition;
        superGaugeVisual += addition;
    }
}

// Function to Add Bar when a move hits
function onHitBar() {
    attackAnimLanded = true;
    attackListen = true;
    //if (attackAnim == 'special_down') {
    //    var cur_anim = self.getAnimation();
    //    if (cur_anim == 'crush_counter') {
    //        superGaugeSprite.currentFrame = superGaugeVisual;
    //        addToGuage(onHitAdd.get(attackAnim));
    //    }

    //} else {
    //    superGaugeSprite.currentFrame = superGaugeVisual;
    //    addToGuage(onHitAdd.get(attackAnim));
    //}
    superGaugeSprite.currentFrame = superGaugeVisual;
    addToGuage(onHitAdd.get(attackAnim));
    
}


function gotHitBar() {
    superAfterImage1.currentFrame = 1;
    superAfterImage2.currentFrame = 1;
    self.getViewRootContainer().removeChild(superAfterImage1);
    self.getViewRootContainer().removeChild(superAfterImage2);
    //Engine.log(event.data.foe);
    attackAnimLanded = false;
    checkWhiff = false;
    attackListen = true;
    superGaugeSprite.currentFrame = superGaugeVisual;
    addToGuage(4);
}

function onLandBar() {
    if (checkWhiff == true && attackAnimLanded == false) {
        attackListen = true;
        checkWhiff = false;
        superGaugeSprite.currentFrame = superGaugeVisual;
        addToGuage(onWhiffAdd.get(attackAnim));
    }
}

// New Input Related Stuff
var clutched = false;
var clutchStates = new StringMap();
clutchStates.set('special_side',38);
clutchStates.set('special_side_air',38);
clutchStates.set('special_down',14);
clutchStates.set('special_up',6);
clutchStates.set('special_up_air',6);
function inputUpdateHook(pressedControls, heldControls) {   
    var pressed_shield_2 = pressedControls.SHIELD2; 
    pressedControls.SHIELD2 = false;
    heldControls.SHIELD2 = false;

    var currentAnim = self.getAnimation();
    
    if (pressed_shield_2 && clutchStates.exists(currentAnim) && clutched == false) {
        if (self.getCurrentFrame() < clutchStates.get(currentAnim)) {
            aud('clutch');
            self.flip();
            clutched = true;
        }
    }
}

function update(){
	if (animTimer > 0) {
        animTimer -= 1;
    } else if (animTimer == 0) {
        attackAnim = self.getAnimation();
        animTimer = -1;
    }

    if ((checkWhiff == true) && (attackAnimLanded == false)) {
        
        if (transitionStates.contains(self.getState())) {
            attackListen = true;
            checkWhiff = false;
            superGaugeSprite.currentFrame = superGaugeVisual;
            addToGuage(onWhiffAdd.get(attackAnim));
        }
    }

    if (attackListen == true) {
        if (self.getPressedControls().ATTACK || self.getPressedControls().SPECIAL || self.getPressedControls().TILT || self.getPressedControls().STRONG) {
            attackListen = false;
            animTimer = 2;
            checkWhiff = true;
            attackAnimLanded = false;
        }

    }
    
    // Clutch Reset
    if (clutched == true) {
        if (clutchStates.exists(self.getAnimation())) {
            if (self.getCurrentFrame() > clutchStates.get(self.getAnimation())) {
                clutched = false;
            }
        }
    }

    if (superGauge > 100) {
        AudioClip.play(self.getResource().getContent('level_up'));
        level += 1;

        if (level == 4) {
            maximumLevel = true;
            superGauge = 101;
            superGaugeVisual = 100;
            self.getDamageCounterContainer().addChild(maximumSprite);
        } else {
            superBar.currentFrame = level;
        }

        superBar.currentFrame = level;
        superGauge -= 100;

    }

    if (superGaugeAnim == 2) {

        if (superGaugeVisual > 100) {
            if (maximumLevel == true) {
                maximumSprite.currentFrame = 1;
            }
            superGaugeVisual -= 100;
            superGaugeSprite.currentFrame = superGaugeVisual;
        } else {
            if (maximumLevel == true) {
                maximumSprite.currentFrame = 2;
            }
            superGaugeVisual += 100;
            superGaugeSprite.currentFrame = superGaugeVisual;
        }
        superGaugeAnim = 0;
    } else {
        superGaugeAnim += 1;
    }
}


function spendBarToMakeBar(levelsSpent) {

    if (maximumLevel == true) {
        self.getDamageCounterContainer().removeChild(maximumSprite);
        maximumLevel = false;
        superGaugeVisual = 1;
    }

    level = level - levelsSpent;
    superBar.currentFrame = level;
    superGaugeSprite.currentFrame = superGaugeVisual;
}

function moveChar(time,x,y,mode) {
    if (mode == 'pause') {
        self.addTimer(1,time,function () {
            actualMoveChar(x,y);
        }, {pauseCondition: () -> self.getHitstop() > 0});
    } else {
            self.addTimer(1,time,function () {
            actualMoveChar(x,y);
        });
    }

}

function actualMoveChar(x,y) {
    if (x != null) {
        if (self.isFacingLeft() == true) {
            self.setXVelocity(x*-1);
        } else {
            self.setXVelocity(x);
        }
    }

    if (y != null) {
        self.setYVelocity(y);
    }
    
}

function onTeardown() {
	
}

