grammar Backtest;

strategyFile
    : STRATEGY STRING LBRACE initialCash? startDate endDate initialBuy rollBlock RBRACE EOF
    ;

initialCash
    : INITIAL_CASH money SEMI
    ;

startDate
    : START DATE SEMI
    ;

endDate
    : END DATE SEMI
    ;

initialBuy
    : BUY NOTIONAL money vanillaSpec SEMI
    ;

rollBlock
    : EVERY DURATION LBRACE SELL POSITION SEMI cashBuy RBRACE
    ;

cashBuy
    : BUY WITH CASH vanillaSpec SEMI
    ;

vanillaSpec
    : VANILLA LPAREN UNDERLYING STRING COMMA KIND OPTION_KIND COMMA STRIKE ATMF COMMA TENOR DURATION RPAREN
    ;

money
    : NUMBER SCALE? MONEY_UNIT
    ;

STRATEGY     : 'strategy';
INITIAL_CASH : 'initial_cash';
BUY          : 'buy';
NOTIONAL     : 'notional';
WITH         : 'with';
CASH         : 'cash';
VANILLA      : 'vanilla';
UNDERLYING   : 'underlying';
KIND         : 'kind';
STRIKE       : 'strike';
ATMF         : 'atmf';
TENOR        : 'tenor';
EVERY        : 'every';
SELL         : 'sell';
POSITION     : 'position';
START        : 'start';
END          : 'end';
OPTION_KIND  : 'call' | 'put';
DURATION     : [0-9]+ [DWMY];
DATE         : [0-9][0-9][0-9][0-9] '-' [0-9][0-9] '-' [0-9][0-9];
MONEY_UNIT   : [A-Z][A-Z][A-Z];
SCALE        : [KMB];
NUMBER       : [0-9]+ ('.' [0-9]+)?;
STRING       : '"' (~["\\] | '\\' .)* '"';
LBRACE       : '{';
RBRACE       : '}';
LPAREN       : '(';
RPAREN       : ')';
COMMA        : ',';
SEMI         : ';';
WS           : [ \t\r\n]+ -> skip;
