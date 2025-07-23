// Animation stats for CharacterTemplate
// Many values are automatically set by our Common class
// Values assigned in this file will override those values
{
	master: {aerialSpeedAcceleration: -1.00, aerialSpeedCap: -1.00, attackId: 0, autoRotate: false, bodyStatus: BodyStatus.NONE, bodyStatusStrength: 0.00,
	chargeFramesMax:0, chargeFramesTotal:0, endType: AnimationEndType.AUTO, grabLimit: 1, gravityMultiplier: 1.00, groundSpeedAcceleration: -1.00,
	groundSpeedCap: -1.00, immovable: false, interruptible: false, landAnimation: 'land_light', landType:LandType.NORMAL, leaveGroundCancel: false, metadata:null,
	name:'Attack Name', nextAnimation: 'Attack2', nextState:CState.JAB, pause: false, resetId: true, resetRotation: false, rotationSpeed: 0.00, shadows: true, slideOff: false,
	solid: true, storedChargePercent: 0.00, terminalVelocity: -1.00, xSpeedConservation: 1.00, ySpeedConservation: 1.00},
	
	//MOTIONS
	stand: {},
	stand_turn: {},
	walk_in: {},
	walk: {},
	walk_out: {},
	dash: {},
	run: {},
	run_turn: {},
	skid: {},
	jump_squat: {},
	jump_in: {},
	jump_midair: {},
	jump_out: {},
	fall_loop: {},
	fall_special: {},
	land_light: {},
	land_heavy: {},
	crouch_in: {},
	crouch_loop: {},
	crouch_out: {},

	//AIRDASHES
	airdash_up: {},
	airdash_down: {},
	airdash_forward: {},
	airdash_back: {},
	airdash_forward_up: {},
	airdash_forward_down: {},
	airdash_back_up: {},
	airdash_back_down: {},

	//DEFENSE
	shield_in: {},
	shield_loop: {},
	shield_hurt: {},
	shield_out: {}, 
	parry_in: {},
	parry_success: {},
	parry_fail: {},
	roll: {},
	spot_dodge: {},

	//ASSIST CALL
	assist_call: {},
	assist_call_air: {},

	//LIGHT ATTACKS
	jab1: {},
	jab2: {},
	jab3: {},
	dash_attack: {xSpeedConservation: 1},
	tilt_forward: {},
	tilt_up: {},
	tilt_down: {},

	//STRONG ATTACKS
	strong_forward_in: {},
	strong_forward_charge: {},
	strong_forward_attack: {},
	strong_up_in: {},
	strong_up_charge: {},
	strong_up_attack: {},
	strong_down_in: {},
	strong_down_charge: {},
	strong_down_attack: {},

	//AERIAL ATTACKS
	aerial_neutral: {},
	aerial_forward: {},
	aerial_back: {},
	aerial_up: {},
	aerial_down: {},

	//AERIAL ATTACK LANDING
	aerial_neutral_land: {},
	aerial_forward_land: {},
	aerial_back_land: {},
	aerial_up_land: {},
	aerial_down_land: {},

	//SPECIAL ATTACKS
	special_neutral: {},
	special_neutral_air: {},
	special_up: {}, 
	special_up_air: {}, 
	special_side: {},
	special_side_air: {}, 
	special_down: {}, 
	special_down_loop: {},
	special_down_endlag: {},
	special_down_air: {},
	special_down_air_loop: {},
	special_down_air_endlag: {},

	//THROWS
	grab: {},
	grab_hold: {},
	throw_forward: {},
	throw_back: {},
	throw_up: {},
	throw_down: {},

	//HURT ANIMATIONS
	hurt_light_low: {},
	hurt_light_middle: {},
	hurt_light_high: {},
	hurt_medium: {},
	hurt_heavy: {},
	hurt_thrown: {},
	tumble: {},

	//CRASH
	crash_bounce: {},
	crash_loop: {},
	crash_get_up: {},
	crash_attack: {},
	crash_roll: {},

	//LEDGE
	ledge_in: {},
	ledge_loop: {},
	ledge_roll: {},
	ledge_climb: {},
	ledge_attack: {},

	//MISC
	revival: {},
	emote: {}
}
