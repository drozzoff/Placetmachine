#
# Define wavelength
#
set lambda [expr 0.025]

#
# Define gradient
#
set gradient [expr 0.072]

#
# Define longrange wakefield
# uncomment next command if single bunch only
#
set scale 1.0
set cav_modes {}
set N_mode 1
for {set i 0} {$i<$N_mode} {incr i} {
    set line "1.0 1.0 1.0"
    lappend cav_modes [expr 0.3/[lindex $line 1]*$scale]
    lappend cav_modes [expr [lindex $line 0]*1e3/$N_mode]
    lappend cav_modes [lindex $line 2]
}

#
# use this list to create fields
#
WakeSet wakelong $cav_modes

#
# define structure
#
InjectorCavityDefine -lambda $lambda -wakelong wakelong
