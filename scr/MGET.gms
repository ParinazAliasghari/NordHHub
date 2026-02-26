$onInline $OFFSYMXREF $Offuelxref $offinclude $offlisting
*option   limrow= 0, limcol= 0, reslim= 300, solprint= off
option   limrow= 30, limcol= 30, reslim= 300

*------------------------------------------------------------------------------*
*----      Scenario and case specification
*------------------------------------------------------------------------------*
*GDXXRW is NOT supported on MAC!!!!
$SETGLOBAL KeepGdx    ''     /* '*' Do not refresh GDX input files, ''  Do refresh GDX input files. */
$SETGLOBAL Verify     '*'     /* '*' Do not verify nodes and arcs sets, '' Do verify nodes and arcs sets, */

$SETGLOBAL path       data              
$SETGLOBAL data       Spain                 /* TEST,MGET,Spain,Blending */
$SETGLOBAL hor        2040                  /* Last year in planning horizon: 2025, 2030, .., 2060 */
$SETGLOBAL oper       4                     /* Operational hours */
$SETGLOBAL scen       2                     /* Decarb & H2 uptake scenario 0 Moderate, 2 Ambitious */
$SETGLOBAL string     %data%_%hor%_%oper%_%scen%   /* Case name string */

*$INCLUDE load_input_%data%.gms
$INCLUDE load_input_from_Excel.gms

*TEST SETTINGS
*r(y) =  1.1-0.1*ORD(y);
*vola2(e)=1;
*e_a(a,e)=0.8;
*scaleUp(h)=1;

*$onText
Binary Variable
    B_BD(a,y)        Indicator for decision to make arc bidirectional
    B_AR(a,e,f,y)    Indicator for arc repurposing decision
    B_WR(n,e,f,y)    Indicator for storage repurposing decision
;
Free variable
    TC                Model objective total costs
;
Positive Variable
    BD(a,y)           Indicator that Arc is bidirectional
    F_A(a,e,y,h)      Flow - hourly
    K_A(a,e,y)        Arc capacity
    K_W(n,e,y)        Working gas capacity
    K_BD(a,e,y)       Volume for volume dependent cost component for making an arc bidirectional
    K_OPP(a,e,y)      Reversed Arc capacity
    K_RA(a,e,f,y)     Repurposed Arc capacity
    K_RW(n,e,f,y)     Repurposed Working gas capacity
    Q_B(n,e,f,y,h)    Energy carrier e blended into f
    Q_E(n,e,y,h)      Storage extraction - hourly
    Q_I(n,e,y,h)      Storage injection - hourly
    Q_P(n,e,y,h)      Production - hourly
    Q_R(n,e,y,h)      Regasification - hourly
    Q_S(n,e,y,h)      Demand covered ('sales') - hourly
    X_A(a,e,y)        Arc expansion
    ZDS(z,n,e,y,h)    Nodal deficits and surpluses
*   ZXA_FS(a,y)       Ensure feasibility arc expansion upper limit
    ZN2               NUTS2 level demand shortage  
;
Equations
    obj             '(1) total costs'
    p_cap           '(2a) production potential'
    p_min           '(2b) minimum production level'
    dmd_n3           '(3a) nodal (NUTS3) demand'
    dmd_n2           '(3b) NUTS2 level demand'
*   dmd_c           (3d) country demand
*   dmd_t           (3e) EU demand,     
    mb              '(4) mass balance'
    max_bl          Limitation for blending in gases
*   storage bounds implemented with direct variable bounds (5a-b)
*    w_inj
*    w_extr
    a_lim           '(6) arc capacity restriction, bidirectional'
    a_opp1          '(7a) Can only use reverse flow if the arc is (made) bidirectional'
    a_opp2          '(7b) Reverse flow capacity usage is restricted by capacity in the opposite direction'
    bd_cost         '(7c) THe largest capacity used in the opposite direction'
    bidir           '(7d) Keeping track whether arc is bidirectional'
    ar_cap          '(8) collect refurbished capacities + new expansion'
    sos_a           '(9) special ordered set 1 - this allows only "one" repurposing'
    sos_w
    bil_a1          '(10a) bi-linear McCormick term 1 - this by itself allows partial repurposing'
    bil_a2          '(10b) bi-linear McCormick term 2 - this by itself allows no or very large repurposing'
    w_lim           Storage capacity restriction
    w_cyc           Storage cycle
    bil_w1
    bil_w2
    wr_cap
*   xa_lb            '(11a) lower bound on arc capacity expansion to represent planned arc capacity expansion' 
*    xa_ub            '(11b) upper bound on arc capacity expansion'
*   Try to reduce feasible region without affecting solution quality:    
*    lim_b_bd        Limit how often an arc can be made bi-directional - should not change the solution    
*    lim_b_ar        Limit how often an arc can be repurposed - may change the solution but not in unreasoble ways
*    lim_b_wr        Limit how often a storage can be repurposed - this may change the solution bot not in unreasonable ways

;

obj..   TC =E=      sum((a,e,y),        r(y)*EOH(y)*c_ax(a,e,y)*    X_A(a,e,y))+
                    sum((a,e,f,y),      r(y)*EOH(y)*f_ar(a,e,f,y)*  B_AR(a,e,f,y))+
                    sum((a,e,f,y),      r(y)*EOH(y)*c_ar(a,e,f,y)*  K_RA(a,e,f,y))+
                    sum((a,y),          r(y)*EOH(y)*f_ab(a,y)*      B_BD(a,y))+
                    sum((a,e,y),        r(y)*EOH(y)*c_ab(a,e,y)*    K_BD(a,e,y))+
                    sum((n,e,y,h),      r(y)*EOH(y)*c_p(n,e,y)*     Q_P(n,e,y,h)     *scaleUp(h))+
                    sum((a,e,y,h),      r(y)*EOH(y)*c_a(a,e,y)*     F_A(a,e,y,h)     *scaleUp(h))+
                    sum((z,n,e,y,h),    r(y)*EOH(y)*c_z(z,e)*       ZDS(z,n,e,y,h)   *scaleUp(h))+
*                   sum((a,y,h),        r(y)*EOH(y)*c_az*           ZXA_FS(a,y)      *scaleUp(h))+
                    sum((nuts2,e,y,h),  r(y)*EOH(y)*c_z('ZD2',e)*    ZN2(nuts2,e,y,h) *scaleUp(h))+
                    sum((n,e,y,h),      r(y)*EOH(y)*c_we(n,e)*      Q_E(n,e,y,h)     *scaleUp(h))+
                    sum((n,e,y,h),      r(y)*EOH(y)*c_lr(n,e)*      Q_R(n,e,y,h)     *scaleUp(h))+
                    sum((n,e,f,y,h),    r(y)*EOH(y)*c_bl(e,f)*      Q_B(n,e,f,y,h)   *scaleUp(h))
;

Q_P.fx(n,e,y,h)$(cap_p(n,e,y,h)<=0)=0;
p_cap(n,e,y,h) $(cap_p(n,e,y,h)>0)..
*    Q_P(n,e,y,h) + sum(f,Q_B(n,e,f,y,h))  =L= cap_p(n,e,y,h) + ZDS('ZPU',n,e,y,h)
*   Q_P(n,e,y,h) + sum(f,Q_B(n,e,f,y,h)) =L= cap_p(n,e,y,h);
    Q_P(n,e,y,h) + sum(f,Q_B(n,e,f,y,h))  =L= cap_p(n,e,y,h)
;

*ZDS.fx('ZPL',n,e,y,h)$(lb_p(n,e,y,h)<=0)=0;
p_min(n,e,y,h)$       (lb_p(n,e,y,h)>0)..
*    Q_P(n,e,y,h) + sum(f,Q_B(n,e,f,y,h)) =G= lb_p(n,e,y,h)  - ZDS('ZPL',n,e,y,h);
     Q_P(n,e,y,h) + sum(f,Q_B(n,e,f,y,h)) =G= lb_p(n,e,y,h);

Q_S.fx(n,e,y,h)     $(not_h(e) AND dmd(n,e,y,h)<=0)=0;
ZDS.fx('ZD2',n,e,y,h)$(not_h(e) AND dmd(n,e,y,h)<=0)=0;
dmd_n3(n,e,y,h)     $(not_h(e) AND dmd(n,e,y,h)>0).. 
     Q_S(n,e,y,h) =E= dmd(n,e,y,h)   - ZDS('ZD2',n,e,y,h);

dmd_n2(nuts2,e,y,h)$(is_h(e) AND dmd2(nuts2,e,y,h))..
    sum(n$n_in_2(n,nuts2),Q_S(n,e,y,h)) =E= dmd2(nuts2,e,y,h) - ZN2(nuts2,e,y,h)
;    

*Q_X.lo(n,e,y,h)=stor_x(n,e,y,h,'lo');
*Q_X.up(n,e,y,h)=stor_x(n,e,y,h,'ub');
*Q_I.lo(n,e,y,h)=stor_i(n,e,y,h,'lo');
*Q_I.up(n,e,y,h)=stor_i(n,e,y,h,'ub');

mb(n,e,y,h)..
*    Q_P(n,e,y,h) + sum(a$a_e(a,n),F_A(a,e,y,h)*e_a(a,e)) + Q_E(n,e,y,h) + ZDS('ZMS',n,e,y,h) + Q_R(n,e,y,h) + sum(f,Q_B(n,f,e,y,h)) =E=
    Q_P(n,e,y,h) + sum(a$a_e(a,n),F_A(a,e,y,h)*e_a(a,e)) + Q_E(n,e,y,h) + Q_R(n,e,y,h) + sum(f,Q_B(n,f,e,y,h)) =E=
    Q_S(n,e,y,h) + sum(a$a_s(a,n),F_A(a,e,y,h))          + Q_I(n,e,y,h) 
*    Q_S(n,e,y,h) + sum(a$a_s(a,n),F_A(a,e,y,h))          + Q_I(n,e,y,h) + ZDS('ZMD',n,e,y,h)
;

Q_B.fx(n,e,f,y,h)$(not_h(e) OR not_g(f))=0;
Q_B.fx(n,e,f,y,h)$(cap_p(n,e,y,h)<=0)   =0;
Q_B.fx(n,e,e,y,h)= 0;
*max_bl(n,e,y,h)$(is_g(e) AND sum(f$is_h(f),cap_p(n,f,y,h))>0)..
*max_bl(n,e,y,h)$is_g(e)..
max_bl(n,f,e,y,h)$(is_h(f) AND is_g(e) AND cap_p(n,f,y,h)>0)..
*    sum(f,Q_B(n,f,e,y,h)) =L=        (Q_S(n,e,y,h) + sum(a$a_s(a,n),F_A(a,e,y,h)) + Q_I(n,e,y,h))
*    sum(f,Q_B(n,f,e,y,h)) =L= ub_bl(e,f)*(Q_S(n,e,y,h) + sum(a$a_s(a,n),F_A(a,e,y,h)) + Q_I(n,e,y,h))
           Q_B(n,f,e,y,h)  =L= ub_bl(f,e)*(Q_S(n,e,y,h) + sum(a$a_s(a,n),F_A(a,e,y,h)) + Q_I(n,e,y,h))
;
*Capacity limit is for gross flows and using capacity also in the other direction if made possible.
a_lim(a,e,y,h)..
*   F_A(a,e,y,h)*vola2(e) =L= K_A(a,e,y) + K_OPP(a,e,y) + ZXA_FS(a,y)
    F_A(a,e,y,h)*vola2(e) =L= K_A(a,e,y) + K_OPP(a,e,y)
;
a_opp1(a,e,y)..
    K_OPP(a,e,y) =L= BD(a,y)*bigM
;
a_opp2(a,e,y)..
    K_OPP(a,e,y) =L= sum(ao$opp(ao,a),K_A(ao,e,y))
;

K_BD.fx(a,e,y)$is_bid(a) =0;
bd_cost(a,e,y,y2)$(yscai(y2,y) AND NOT is_bid(a))..
   K_BD(a,e,y)  =G= K_OPP(a,e,y2) - (1-B_BD(a,y))*bigM
;

BD.up(a,y)=1;
*If already bidirectional, assign that
BD.fx(a,y)$is_bid(a)=   1;
*B_BD.fx(a,y)$(ORD(y)=1 AND is_bid(a))=is_bid(a);

bidir(a,y)$(NOT is_bid(a))..
    BD(a,y) =L=  B_BD(a ,y)+sum(y2$ypred(y2,y),BD(a ,y2)) 
;

*First period capacity is given by input data
K_A.fx(a,e,y)$(ORD(y)=1) = cap_a (a,e,y);
K_W.fx(n,e,y)$(ORD(y)=1) = cap_ww(n,e,y);
*Capacity is all capacity (re)purposed to the current carrier and whatever is invested specific for the current carrier
ar_cap(a,e,y)$(ord(y)>1)..      K_A(a,e,y) =E= sum(f, K_RA(a,f,e,y))+sum(y2$ypred(y2,y), X_A(a,e,y2));
wr_cap(n,e,y)$(ord(y)>1)..      K_W(n,e,y) =E= sum(f, K_RW(n,f,e,y));

*No natural gas inflow into France in any year
*K_A.fx(a,e,y)$  (is_g(e) AND sum(m$n_in_c(m,'FR'), a_e(a,m)))=0;
*K_OPP.fx(a,e,y)$(is_g(e) AND sum(m$n_in_c(m,'FR'), a_e(a,m)))=0;


*Only one (re)purposing destination:
sos_a(a,e,y)$(ord(y)>1)..         sum(f,B_AR(a,e,f,y)) =E= 1;
sos_w(n,e,y)$(ord(y)>1)..         sum(f,B_WR(n,e,f,y)) =E= 1;

*No repurposing in the first period
B_AR.fx(a,e,e,y)$(ORD(y)=1)=0;
K_RA.fx(a,e,f,y)$(ORD(y)=1)=0;
B_WR.fx(n,e,e,y)$(ORD(y)=1)=0;
K_RW.fx(n,e,f,y)$(ORD(y)=1)=0;

*Can only make bidirectional if "Reversable?" - TO DO
*Can only repurpose arc if "H2-ready" - TO DO
*Can only repurpose storage if H2-ready 
K_W.fx(n,'G',y)     $(dat_w(n,'G','H2-ready')<=0)=cap_ww(n,'G',y);
*K_RW.fx(n,'G','G',y)$(dat_w(n,'G','H2-ready')<=0)=cap_ww(n,'G',y);

*K_W.fx(n,'H',y)=cap_ww(n,'H',y);

*Sum of repurposing capacities away from the specific carriers equals the previous period carrier capacity
bil_a1(a,e,y)$(ord(y)>1)..     sum(f,K_RA(a,e,f,y)) =E= sum(y2$ypred(y2,y), K_A(a,e,y2));
bil_w1(n,e,y)$(ORD(y)>1)..     sum(f,K_RW(n,e,f,y)) =E= sum(y2$ypred(y2,y), K_W(n,e,y2));

*Only the specific repurposing can get the capacity
bil_a2(a,e,f,y)$(ord(y)>1)..    K_RA(a,e,f,y) =L= B_AR(a,e,f,y)*bigM;
bil_w2(n,e,f,y)$(ord(y)>1)..    K_RW(n,e,f,y) =L= B_WR(n,e,f,y)*bigM;

*xa_lb(a,e,y)$(lb_ax(a,e,y)>0)..
*    X_A(a,e,y)  =G= lb_axa(a,e,y)
*;
*xa_ub(a,y)$(ub_ax(a,y)+sum(ao$opp(ao,a),ub_axa(ao,y))>0)..
*    sum(e,X_A(a,e,y)+sum(ao$opp(ao,a),X_A(ao,e,y))) =L= ub_ax(a,y)+sum(ao$opp(ao,a),ub_ax(ao,y))+XA_FS(a,y);
*;

*Regasifier capacity limit
Q_R.up(n,e,y,h)=dat_r(n,e,'2025','ub');
*Injection and extraction capacity limit; currently not adjustable. Vols2(e) adjusted in input data assignments
Q_I.up(n,e,y,h)=cap_wi(n,e,y);
Q_E.up(n,e,y,h)=cap_we(n,e,y);

*Q_I.fx(n,e,y,h)$(cap_ww(n,e,y)<=0)=0;
*Q_E.fx(n,e,y,h)$(cap_ww(n,e,y)<=0)=0;

*Capacity can be repurposed so no conditional $cap_ww(n,e,y)
w_lim(n,e,y)..      sum(h,scaleUp(h)*Q_E(n,e,y,h))*vols2(e) =L= K_W(n,e,y);
w_cyc(n,e,y)..      sum(h,scaleUp(h)*Q_E(n,e,y,h))          =E= e_w(n,e)*sum(h,scaleUp(h)*Q_I(n,e,y,h));


** LIMIT HOW OFTEN THINGS MAY HAPPEN **
*One of these makes the problem infeasible - leave out for now.
** decision to make arc bidirectional
*lim_b_bd(a)..       sum(y,      B_BD(a,y))      =L= 1;
** arc repurposing decision
*lim_b_ar(a)..       sum((e,f,y),B_AR(a,e,f,y))  =L= 1;
** storage repurposing decision
*lim_b_wr(n)..       sum((e,f,y),B_WR(n,e,f,y))  =L= 1;    

*option Q_B:0:0:1; display Q_B.l;

*$ontext
*option mip=xpress, limrow=20,limcol=20;
option reslim=7200;
*option reslim=30;
option mip=cplex, limrow=1E3,limcol=1E3;
model MGET /all/;
solve MGET min TC using MIP;

$INCLUDE report.gms
*$INCLUDE create_excel_input_gdx.gms

*display e_a, B_AR.l, B_BD.l, BD.l, K_A.l, K_OPP.l, K_BD.l, K_RA.l, Q_P.l, Q_S.l, X_A.l, F_A.l, ZDS.l
;
execute_unload 'gdx/%string%_var',
    BD,
    F_A, K_A, K_OPP, K_BD, K_RA, Q_B, Q_P, Q_S, X_A,
    ZDS,
*    ZXA_FS
    B_AR, B_BD, TC
;

parameter flag;
flag('Infeasible?')= sum((z,n,e,y,h), ZDS.l(z,n,e,y,h));
display 'If flag is positive, check reports for surpluses and deficits', flag;

$onText
$offText

