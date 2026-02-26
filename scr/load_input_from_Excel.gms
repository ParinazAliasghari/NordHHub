Display "Just check the GDX Files ($gdxIn) E:\Dropbox\MGET\GAMS\gdx\%data%.gdx and gdx/%string%_inputs"
;
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*-*          READ EXCEL FILE
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
%KeepGdx%$call "GDXXRW %path%/%data%.xlsx O=gdx/%data% SkipEmpty=0 @read_data.txt"
%KeepGdx%$ifE errorLevel<>0 $abort.noError 'Something wrong reading Excel, see message(s) above. NB GDXXRW is NOT supported on MAC!!!! NB2 Bad data range may mean you have not saved the file after changing a Named Excel range'

Set
    aux_tot "Auxiliary set for label order"    /TOT,Obj,Idx,''/
    A       "Arcs; if reversable define the other direction too"
    CN      "Countries"
    F       "Fuels / Energy carriers"
    N       "Nodes (NUTS3 level)"
    NUTS2   NUTS2 regions
    RGN     "Regions"
    Z       "Surplus / deficit penalty types"
    aux_rep "Auxiliary set for label order"   /TOT,nom,disc,'+','-','Z','K','0',
    'purp-','purp+',purp,bidir,'cap',capBD,1,2,3,4,5,6,7,8,'expans', P,D,D2,LNG,A,A+,A-,'C','G','H',W,P+,M+,Z+,P-,Z-,D-/
    aux_rep_c /prod,flow+,flow-,expans+,expans-, purp,repurp,bidir,bidfx,invest,Stor,Regas,Blend,ZXA,ZN2,ZA,ZD,ZMD,ZMS,ZPL,ZPU/
;
alias (a,ao,ai),(e,f),(n,m),(rgn,ro,ri),(cn,c)
;
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*-*          TIME STRUCTURE AND DISCOUNTING
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
$INCLUDE data/%hor%.gms              /* load the years set */
set H hours /1*%oper%/
;
ALIAS (y,y2),(yrep,yrep2),(h,h2)
;
Parameter
    ypred(y,y)      "Immediate predecessor year"
    yscai(y,y)      "All successors including the current year"
    EOH(y)          "End of Horizon correction"
;
ypred(y2,y)$(ord(y)-ord(y2)=1)=1;
yscai(y2,y)$(ord(y)<=ord(y2))= 1;

EOH(y)=1;
*2050 --> extrapolate. TO DO; make this into a value read from dat_o 
EOH(y)$(ord(y)=card(y))=3;

*$ontext
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*            LOAD AND ASSIGN OTHER DATA
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
Parameter
    dat_o            "Other data =dat_o('','','');"
    bigM             "bigM"
    c_bl            Blending cost
    c_z(z,e)         "Feasibility penalties"
    is_g(e)          Is natural gas
    is_h(e)          Is hydrogen
    not_g(e)         Not natural gas   
    not_h(e)         Not hydrogen   
    r(y)             "discount factor"
    vola2(e)         "energy to arc volume unit conversion, relative to g"
    vols2(e)         "energy to storage volume unit conversion, relative to g"
    scaleUp(h)         "Number of hours represented by this hour"
;    
$gdxin gdx/%data%
$load  dat_o,f,z
;

dat_o('BlendCost',e,f)$(dat_o('BlendCost',e,f)<=0)=dat_o('BlendCost','','');
c_bl(e,f)= dat_o('BlendCost',e,f);

is_g('G')= 1;
is_h('H')= 1;
not_g(e)=  1; not_g('G')=0;
not_h(e)=  1; not_h('H')=0;

bigM=dat_o('bigM','','');
dat_o('Penalty',z,e)$(dat_o('Penalty',z,e)<=0)=dat_o('Penalty',z ,'');
dat_o('Penalty',z,e)$(dat_o('Penalty',z,e)<=0)=dat_o('Penalty','','');
c_z(z,e)=dat_o('Penalty',z,e);


r(y) =  1/power(1+dat_o('DiscRate','',''),dat_o('YearStep','','')*(ORD(y)-1));
vola2(e)=1; vola2(e)$dat_o('vola2',e,'')=dat_o('vola2',e,'');
vols2(e)=1; vols2(e)$dat_o('vols2',e,'')=dat_o('vols2',e,'');

*Winter, Summer, Shoulder, Minimum
*scaleUp(h)=dat_o('scale',h,'')*8760/sum(h2,scaleUp(h2));  
scaleUp(h)=dat_o('scale',h,'');  

*$ontext
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*            LOAD AND ASSIGN NODES DATA
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
Parameter
    cap_p(n,e,y,h)  Supply capacity
    c_lr            Regasification costs
    c_p(n,e,y)      "supply unit cost"
    dat_c           Demand data loaded from Excel
    dat_n           Nodes data loaded from Excel
    dat_p           Supply data loaded from Excel
    dat_r           Regasifier data loaded from Excel
    dmd(n,e,y,h)      NUTS3 Demand (potential)
    dmd2(nuts2,e,y,h) NUTS2 level demand (hydrogen)
    lb_p(n,e,y,h)   lower bound supply
    ub_bl           upper bound blending fraction - energy content
    n_in_c(n,c)     node in country
    n_in_2(n,nuts2) node in nuts2
    n_in_r(n,rgn)   node in region
;
$gdxin gdx/%data%
$load  n,cn,rgn,nuts2,dat_n,dat_p,dat_r,dat_c
;

*$ontext
n_in_2(n,nuts2)$sum((c,rgn),    abs(dat_n(n,c,nuts2,rgn,'LAT')))=1;
n_in_c(n,c)$    sum((nuts2,rgn),abs(dat_n(n,c,nuts2,rgn,'LAT')))=1;
n_in_r(n,rgn)$  sum((nuts2,c),  abs(dat_n(n,c,nuts2,rgn,'LAT')))=1;

c_p(n,e,y)=            dat_p(n,e,y,'MC');
c_p(n,e,y)$(ord(y)>2)= dat_p(n,e,'2030','MC'); 

*Only first year first hour capacities in Excel
cap_p(n,e,y,h)=   dat_p(n,e,y,       '1');
cap_p(n,'g',y,h)$(ord(y)>=2)= dat_p(n,'g','2025','1');

*Algerian gas supply
cap_p('DZ000','G',y,h)$(ord(y) =2)= 1.0*cap_p('DZ000','G','2025',h);
cap_p('DZ000','G',y,h)$(ord(y) =3)= 0.8*cap_p('DZ000','G','2025',h);
cap_p('DZ000','G',y,h)$(ord(y) =4)= 0.7*cap_p('DZ000','G','2025',h);
cap_p('DZ000','G',y,h)$(ord(y) =5)= 0.6*cap_p('DZ000','G','2025',h);
cap_p('DZ000','G',y,h)$(ord(y)>=6)= 0.5*cap_p('DZ000','G','2025',h);


lb_p(n,e,y,h)=  dat_p(n,e,y,'LB');

*File "Future supply potentials rough estimate.xlsx"

*PT16E production (wind) / import
*PT186   production (solar) & export 
*PT181  Sines - export & supply 
*ES112   production (solar)
*ES120   production (wind) / import
*ES130   production (wind) / import
*ES418   production (solar)
*ES422   production (solar/wind)
*ES620   production (wind) / import
*ES511   export
*ES615   production (?) / import

*DZ000  Algeria

Table sup_aux Hydrogen supply potential
          2035 2040 2045 2050   MC
PT16E     0.1   0.2  0.5  1.0    2 
PT181     0.4   0.6  0.8  1.0    2 
PT186     0.2   0.3  0.4  0.5    2 
ES112     0.2   0.3  0.4  0.5    2 
ES120     0.2   0.3  0.4  0.5    2 
ES130     0.2   0.3  0.4  0.5    2 
ES418     0.2   0.3  0.4  0.5    2 
ES422     0.2   0.3  0.4  0.5    2 
ES615     0.2   0.3  0.4  0.5    2 
ES620     0.2   0.3  0.4  0.5    2 
DZ000     0.1   0.2  0.5  1.0   10 
;

$INCLUDE data/scen_%string%_sup.gms

*lb_p(n,e,y,h)$(n_in_c(n,'ES') AND is_h(e))=cap_p(n,e,y,h);
*lb_p(n,e,y,h)$(n_in_c(n,'ES') AND is_h(e) AND cap_p(n,e,y,h))=1E-2;

*lb_p(n,e,y,h)$(n_in_c(n,'FR') AND is_h(e))=min(1,cap_p(n,e,y,h));
*lb_p(n,e,y,h)$(n_in_c(n,'FR') AND is_h(e) AND ORD(y)>1)=min(1,0.1*cap_p(n,e,y,h));

lb_p(n,e,y,h)=min(lb_p(n,e,y,h),cap_p(n,e,y,h));

dat_o('BlendLim',e,f)$(dat_o('BlendLim',e,f)<=0)=dat_o('BlendLim','','');
ub_bl(e,f)=dat_o('BlendLim',e,f);

$ontext
1 Winter, 2 Summer, 3 Shoulder, 4 MIN
$offtext

$INCLUDE data/scen_%string%_dmd.gms


*Regas -
dat_r(n,e,'2025','cal_c')$(dat_r(n,e,'2025','cal_c')<=0)=1;
c_lr(n,e)= 1* dat_r(n,e,'2025','cal_c');
c_lr(n,e)$not_g(e)= 9999;

*$ontext
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*            LOAD AND ASSIGN ARCS DATA
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
Parameter
    a_s(a,n)        "arc start node"
    a_e(a,n)        "arc end node"
    anm(a,n,m)      "Arc exists between nodes n and m"
    cap_a(a,e,y)    "Arc capacity flow limit - volumetric"
    c_a(a,e,y)      "arc usage unit cost; multiply by vola2?!?!"
    c_az            
    c_ab(a,e,y)      "Half ? of the bidirectional unit cost - I think I corrected this, see cost report"
    dat_a           Arcs data loaded from Excel
    dat_ao          Arcs start and end nodes to define opposite direction arcs.
*   dat_k           Arc capacities data loaded from Excel
*   dat_x           Arc expansions data loaded from Excel
    f_ab(a,y)        "Half ? of the bidirectional fixed cost - I think I corrected this, see cost report"
    c_ar(a,e,f,y)    "repurpose unit cost"
    f_ar(a,e,f,y)    "repurpose fixed cost"
    c_ax(a,e,y)      "arc expansion unit cost, there is no fixed cost component"
    e_a(a,e)        "arc flow efficiency"
    lb_ax(a,e,y)     "Lower bound planned expansion"
    ub_ax(a,y)       "Arc expansion limit - volumetric"
    opp(a,a)        "Arc in the opposite direction"
    scaleUp(h)        "Number of hours represented by this hour"
    is_bid(a)         Arc is bidirectional  
;
$gdxin gdx/%data%
$load  a,dat_a
*,dat_k,dat_x
;

a_s(a,n)$(sum((m,e),dat_a(a,n,m,e,'len')+dat_a(a,n,m,e,'cap'))>0)=1;
a_e(a,m)$(sum((n,e),dat_a(a,n,m,e,'len')+dat_a(a,n,m,e,'cap'))>0)=1;

anm(a,n,m)$(a_s(a,n) AND a_e(a,m))=1;

loop {(ai,ao,n,m)$(anm(ai,n,m) AND anm(ao,m,n)),
    opp(ai,ao)=1;
    opp(ao,ai)=1;
};

*option anm:0:0:1, a_e:0:0:1, a_s:0:0:1, opp:0:0:1; display anm,a_e,a_s,opp;
*abort "always 13 jun 2024";

c_az=dat_o('Penalty','ZA','');

*Assign default values wherever applicable
dat_o('BFPipe',e,'')$  (dat_o('BFPipe',e,   '')<=0)= dat_o('BFPipe','',   '');
dat_o('BLPipe',e,'')$  (dat_o('BLPipe',e,   '')<=0)= dat_o('BLPipe','',   '');
dat_o('BIPipe',e,'')$  (dat_o('BIPipe',e,   '')<=0)= dat_o('BIPipe','',   '');
dat_o('Bidir','Var',e)$(dat_o('Bidir','Var',e)<=0)=  dat_o('Bidir','Var', '');
dat_o('RepurpArc',e,f)$(dat_o('RepurpArc',e,f)<=0)=  dat_o('RepurpArc','','');
dat_o('RepurpArc',e,e)=0;
*Instead of subtracting 1 everywhere else
dat_o('OffshMult','','')=max(0,dat_o('OffshMult','','')-1);

*Offshore part cannot be longer than total length
dat_a(a,n,m,e,'off')=min(dat_a(a,n,m,e,'len'),dat_a(a,n,m,e,'off'));

*$ontext
*Currently arcs in the data set several times for different fuels NOT POSSIBLE
*dat_a(a,n,m,'','len')=sum(e,dat_a(a,n,m,e,'len'))/sum((a,n,m)$(anm(a,n,m)),anm(a,n,m));
dat_a(a,n,m,'','len')=sum(e,dat_a(a,n,m,e,'len'));
*dat_a(a,n,m,'','off')=sum(e,dat_a(a,n,m,e,'off'))/sum((a,n,m)$(anm(a,n,m)),anm(a,n,m));
dat_a(a,n,m,'','off')=sum(e,dat_a(a,n,m,e,'off'));


dat_a(a,n,m,e,'cal_b')$(dat_a(a,n,m,e,'cal_b')<=0)=1;
dat_a(a,n,m,e,'cal_c')$(dat_a(a,n,m,e,'cal_c')<=0)=1;
dat_a(a,n,m,e,'cal_l')$(dat_a(a,n,m,e,'cal_l')<=0)=1;
dat_a(a,n,m,e,'cal_r')$(dat_a(a,n,m,e,'cal_r')<=0)=1;
dat_a(a,n,m,e,'cal_x')$(dat_a(a,n,m,e,'cal_x')<=0)=1;
               
loop {(a,n,m)$anm(a,n,m),
    
    cap_a(a,e,y)=dat_a(a,n,m,e,'cap');
    
    is_bid(a)$sum(e,dat_a(a,n,m,e,'bidir')) =1;
    
    c_a(a,e,y)=  dat_o('BFPipe',e,'')*vola2(e)*
                 (dat_a(a,n,m,'','len')+dat_o('OffshMult','','')*dat_a(a,n,m,'','off'))*dat_a(a,n,m,e,'cal_c')
                 /dat_o('Pipe','Len','Std')
;
*scaleUp investment costs, with YearStep, but not with operational hours
*    c_ax(a,e,y)=  dat_o('BIPipe',e,'')*vola2(e)*
*Capacity limit considers vola2, so no need to also scale expansion costs
    c_ax(a,e,y)=  dat_o('BIPipe',e,'')*
                 (dat_a(a,n,m,'','len')+dat_o('OffshMult','','')*dat_a(a,n,m,'','off'))*dat_a(a,n,m,e,'cal_x')
                 /dat_o('Pipe','Len','Std')
                 /dat_o('YearStep','','')
;
                    
    e_a(a,e)=  max(1-dat_o('LossMax','',''),
                   1-dat_o('BLPipe',e,'')*dat_a(a,n,m,'','len')*dat_a(a,n,m,e,'cal_l')
                    /dat_o('Pipe','Len','Std')
                  );
    c_ab(a,e,y)=    dat_o('Bidir','Var',e)*
                    (dat_a(a,n,m,'','len')+dat_a(a,n,m,'','off'))*dat_a(a,n,m,e,'cal_b')
                    /dat_o('Pipe','Len','Std')/dat_o('YearStep','','');

    f_ab(a,y)=       dat_o('Bidir','Fix','')
                    /dat_o('YearStep','','');

    c_ar(a,e,f,y)=   dat_o('RepurpArc',e,f)*
                    (dat_a(a,n,m,'','len')+dat_o('OffshMult','','')*dat_a(a,n,m,'','off'))
                    /dat_o('Pipe','Len','Std')
                    *dat_a(a,n,m,e,'cal_r')
                    /dat_o('YearStep','','');
                    
    f_ar(a,e,f,y)=   dat_o('RepurpArc','Fix',f)*
                     dat_a(a,n,m,e,'cal_r')
                    /dat_o('YearStep','','');

*Override for now
*    lb_ax(a,e,y)= dat_x(a,e,'lb',y);
     lb_ax(a,e,y)= 0;
*    ub_ax(a,y)  = dat_x(a,'TOT','ub',y);
     ub_ax(a,y) = +inf;
};

*Assign values opposite arcs
loop{(ai,ao,e,y)$(opp(ai,ao) AND c_a(ai,e,y)>0 AND c_a(ao,e,y)<=1E-5),
    c_a  (ao,e,y)=   c_a  (ai,e,y);
    c_ax (ao,e,y)=   c_ax (ai,e,y);
    e_a  (ao,e)=     e_a  (ai,e);
    c_ab (ao,e,y)=   c_ab (ai,e,y);
    f_ab (ao,y)=     f_ab (ai,y);
    c_ar (ao,e,f,y)= c_ar (ai,e,f,y);
    f_ar (ao,e,f,y)= f_ar (ai,e,f,y);
    lb_ax(ao,e,y)=   lb_ax(ai,e,y);
    ub_ax(ao,y)=     ub_ax(ai,y);
    is_bid(ao)=      is_bid(ai);
};

c_ar(a,e,e,y)=0;
f_ar(a,e,e,y)=0;

*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
*            LOAD AND ASSIGN STORAGE DATA
*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
Parameter
    dat_w           Storage data loaded from Excel
    cap_we          Storage extraction cap (hourly)
    cap_wi          Storage injection cap (hourly)
    cap_ww          Storage working gas cap (total)
    e_w(n,e)        Storage efficiency
    c_we(n,e)       Extraction costs
    stor_i(n,e,y,h,*) storage injection data
    stor_x(n,e,y,h,*) storage extraction data
    
;
$gdxin gdx/%data%
$load  dat_w
;

dat_w(n,e,'cal_c')$(dat_w(n,e,'cal_c')<=0)=1;
dat_w(n,e,'cal_l')$(dat_w(n,e,'cal_l')< 0)=1;

cap_we(n,e,y)= dat_w(n,e,'X');
cap_we(n,e,y)$(dat_w(n,e,'X')<=0 AND is_h(e))= dat_w(n,'G','X')/vols2('H');
cap_we(n,e,y)$(dat_w(n,e,'X')<=0 AND is_g(e))= dat_w(n,'H','X')*vols2('H');

cap_wi(n,e,y)= dat_w(n,e,'I');
cap_wi(n,e,y)$(dat_w(n,e,'I')<=0 AND is_h(e))= dat_w(n,'G','I')/vols2('H');
cap_wi(n,e,y)$(dat_w(n,e,'I')<=0 AND is_g(e))= dat_w(n,'H','I')*vols2('H');

cap_ww(n,e,y)=dat_w(n,e,'W')*sum(h,scaleUp(h))/8760;

*Hard coded storage loss rate %; TO DO use LossMax
dat_w(n,e,'cal_l')$(dat_w(n,e,'cal_l')<=0)=1;
e_w(n,e)=   1-0.01*dat_w(n,e,'cal_l');
*Hard coded storage extraction costs
c_we(n,e)=  1.00  *vols2(e)*dat_w(n,e,'cal_c');

$onText
stor_x(n,e,y,h,'lb')=    dat_w(n,e,y,h,'X','lb');
stor_x(n,e,y,h,'ub')=max(dat_w(n,e,y,h,'X','ub'),
                         dat_w(n,e,y,h,'X','lb'));
stor_i(n,e,y,h,'lb')=    dat_w(n,e,y,h,'I','lb');
stor_i(n,e,y,h,'ub')=max(dat_w(n,e,y,h,'I','ub'),
                         dat_w(n,e,y,h,'I','lb'));

$onText
$offText
%Verify%$INCLUDE Verify_nodes_arcs.gms

parameter rep_a;
rep_a(a,y,n,m,e,'cap')    $(a_s(a,n)=1 AND a_e(a,m)=1)=     cap_a(a,e,y);
rep_a(a,y,n,m,e,'x_u')    $(a_s(a,n)=1 AND a_e(a,m)=1)=     ub_ax(a,y);
rep_a(a,y,n,m,e,'x_l')    $(a_s(a,n)=1 AND a_e(a,m)=1)=     lb_ax(a,e,y);
rep_a(a,y,n,m,e,'opp')    $(a_s(a,n)=1 AND a_e(a,m)=1)=     sum(ao$opp(ao,a),cap_a(ao,e,y));

execute_unload 'gdx/%string%_inputs',
        a
        a_e
        a_s
        anm
        bigM,
        c,
        c_a
        c_ab
        c_ar,
        c_ax
        c_az
        c_bl
        c_lr
        c_p,
        c_z,
        cap_a
        cap_p,
        cap_we
        cap_wi
        cap_ww
        cn,
        dat_o,
        dmd,
        dmd2
        e_a
        e_w
        f,
        f_ab
        f_ar
        h,
        is_bid
        lb_ax
        n,
        n_in_2,
        n_in_c,
        n_in_r,
        nuts2,
        opp
        r,
        rep_a
        rgn,
        scaleUp,
        stor_i
        stor_x,
        ub_ax
        ub_bl
        vola2,
        vols2,
        y,
        ypred,
        yrep,
        yscai
;
