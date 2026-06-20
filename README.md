# A Compiler Built from Scratch

This repository documents my progress in building a compiler from scratch. It's purpose is to increase my understanding of compiler technology and exhibit my technical skills. The compiler implements a custom, high level, imperative programming language with monomorphic functions and inferred types.

Stages:  
&emsp;&emsp;✅ Lexing  
&emsp;&emsp;✅ Parsing  
&emsp;&emsp;✅ Semantic analysis  
&emsp;&emsp;🛠️ Code generation     

The individual components can be imported as modules and there is a script called main.py that performs lexing, parsing and semantic analysis on a sample program.

Below is an explanation of the design. I started this project with zero understanding of compiler and programming langauge theory, and while not perfect, I have considered the consequences of the architecture and the efficiency of implementations. If you are particularly intrested in the software construction and algorithm design, as opposed to the compiler theory, read sections:  
  
&emsp;&emsp;* Prototyping the Lexer  
&emsp;&emsp;* Lexing Logic and State Table Construction  
&emsp;&emsp;* Parse Table Construction  
&emsp;&emsp;* Parsing Logic  
&emsp;&emsp;* Modified Parser Architecture and Implementation  

## Lexer

### Regular Expressions

The design process starts by writing regular expressions which are capable of expressing the set of tokens my lexer should recognise. 


### Converting the Regular Expressions to Nondeterministic Finite Automata (NFA)

Converting these regular expressions to NFA resulted in unmanageable complexity due to the combinatorial explosion of branching as a result of using raw regular expressions. I decided to use character classes defined in regular defintions as transitions in the NFA. This choice reduces the complexity of the NFA but requires us to resolve which character belongs to which transition (you will see later that I chose to resolve this by preprocessing the state table). 


### Converting the NFA into a Deterministic Finite Automaton (DFA) by Subset Construction

By finding the epsilon colsure of each transtion in the NFA we can generate a DFA. I do this recursively until all states transiton to a state thats already been defined in the DFA.


### Prototyping the Lexer 

I learned three things from prototyping the lexer.
1. keywords should be recognised as IDs and checked against hardcoded keywords.
2. The state table should be processed to flatten the transition classes into individual characters.
3. Use disjoint character classes on the first state of the combined NFA (this is possible because of 1.)

(1.) Simplifies subset construction at the expense of a couple of lines of extra code in the lexer. (2.) Removes the runtime logic in the lexer needed to resolve whether a character belongs to a transition class. This makes the lexer logic more readable and allows for an average case O(1) lookup. (3.) Reduces the complexity of token creation by removing the need for priority rules based on token type. The lexer can naturally take the longest token once no more transitions are possible.


### Finalised Automata
With these contraints the finalised regular defintions NFAs and DFA are below. (note the DFA is not drawn, all information required to implement the state table is present in the subset construction.)


#### Regular Definitions
```
letters_ -> [a-zA-Z_]      
digits   -> [0-9]  
ID       -> letters_(letters_|digits)* 

digits         -> [0-9]  
digits_not_0   -> [1-9]  
number_literal -> (0|digits_not_0digits)*)(.digits⁺)?

ascii          -> [\x00-\x7F]  
string_literal -> "ascii*"

op -> [+|-|*|/|=|>|<|||&|!|%]

punctuatuon -> [(|)|;|:|,|[|]|{|}]

whitespace -> [ |\t|\n|\r]
```
#### NFA

<img src="assets/NFA.png" alt="assets/NFA.png" width="400"/>

#### Subset Construction/DFA

```
S1 = {1, 10, 11}  

δ(S1, letters_) = S2 = {2, 3, 4, 6, 9}  
δ(S1, digits_not_0) = S3 = {12, 14, 16, 17, 18, 21}  
δ(S1, 0) = S4 = {13, 17, 18, 21}  
δ(S1, ") = S5 = {22, 23, 25}  
δ(S1, op) = S6 = {27}  
δ(S1, punctuation) = S7 = {28}  
δ(S1, whitespace) = S8 = {29}  

δ(S2, letters_) = S9 = {5, 8, 3, 4, 6, 9}  
δ(S2, digits) = S10 = {7, 8, 3, 4, 6, 9}  

δ(S3, digits) = S11 = {15, 14, 16, 17, 18, 21}  
δ(S3, .) = S12 = {19}  

δ(S4, .) = S13 = S12  

δ(S5, ascii) = S13 = {24, 23, 25}  
δ(S5, ") = S14 = {26}  

δ(S9, letters_) = S9   
δ(S9, digits) = S10  

δ(S10, letters_) = S9   
δ(S10, digits) = S10  

δ(S11, digits) = S11  
δ(S11, .) = S12  

δ(S12, digits) = S15 = {20, 19, 21}  

δ(S13, ascii) = S13  
δ(S13, ") = S14  

δ(S15, digits) = S15  
```
### Lexing Logic and State Table Construction

The `raw_state_table` is implemented as a nested dictionary in `raw_state_table.py` allowing it to be accessed with meaninful names in constant time on average.  This results in a data structure that is readable and efficient. Rather than hardcoding the transition classes at each state, I use a separate dictionary, `transition_classes`, to encapsulate them. The values of of the transition classes are implemented as strings for fast iteration. An Enum is used for the transition class keys to encapsulate key definitions which increases maintainability and reduces errors from mispelled/invalid keys. The `lexer` code is designed to be as clean as possible and lives in `lexer.py`. It loops through all characters in the input following the transitions defined in the state table. I used the `.get` method to look up the next state, which returns gracefully if there is no transition in the current state matching the current character. If it transitions to another state, it tries to access the the type of token accepeted at this state. If this state is not accepting, `.get` returns None and it loops. This process continues until there are no transitions left to make. If we have encoutered an accepting state, we create and store the token and reset the state variables to process the rest of the input.

### Token Representation

Tokens are represented by a `Token` class that inherits from `tuple`. The underlying tuple holds exactly two elements — the token type and the token value — which means a `Token` compares equal to a plain `(type, value)` tuple and supports the same unpacking. Source position is stored as extra instance attributes, `.line` and `.col`, that sit alongside the tuple without affecting equality. This design was chosen over a namedtuple or dataclass because it avoids any changes to the parser or tests, both of which were written to expect 2-tuples.

Token creation is handled by a classmethod `Token.from_dfa` which encapsulates the post-processing logic: keyword identifiers and operators are self-typed (type equals value), whitespace is discarded, and everything else uses the DFA token type name. Putting this logic on the class is cleaner than a standalone `create_token` function that mutates an external list.

## Parser
The parser takes a sequence of tokens from the lexer, determines whether it is a well formed program and outputs a syntax tree. I opted for a parsing architecture which is designed to parse a particular class of grammars called LL(1). This choice was made because LL(1) parsers are as fast as practical alternatives such as LALR(1) and LR(1) but are simpler to implement by hand. The tradeoff is that LL(1) grammars are more restrictive than other classes of grammars because they must be free of left recursion, be fully left factored and have no first/follow conflicts. Building a grammar appropriate for a LL(1) parser requires a careful and iterative design process, and the grammar may be less expressive than one may hope for a modern programming language.

### Building a Grammar 
Building the parser starts with a general description of how a valid program can be structured. This description is called a grammar. After some iteration I produced the grammar below, which is almost LL(1) except for the ambiguity detailed in the comment above the ExprRest production. This ambiguity is resolved in the parse table construction below so that an LL(1) parsing algorithm can still be employed.

```
P        -> StmtList
StmtList -> Stmt StmtList | ε
Stmt     -> FuncDef | Expr | Assign | Conditional

FuncDef      -> FUNC ID ( Params ) { FuncBody }
FuncBody     -> FuncEntry FuncBody | ε
FuncEntry    -> Expr | FuncDef | RETURN Expr | Assign | Conditional 

Params                   -> ParamList KeyWordParamListTail | KeyWordParamList | ε
ParamList                -> Param ParamListRest
ParamListRest            -> , Param ParamListRest | ε
KeyWordParamListTail     -> | KeyWordParam KeyWordParamListTailRest | ε
KeyWordParamListTailRest -> , KeyWordParam KeyWordParamListTailRest | ε
KeyWordParamList         -> KeyWordParam KeyWordParamListRest
KeyWordParamListRest     -> , KeyWordParam KeyWordParamListRest | ε
Param                    -> ID
KeyWordParam             -> Assign

Assign -> ASSIGN ID = Expr

Expr            -> Term ExprRest
#ExprRest is not strictly ll(1) because ExprRest =>* ε, and first(AddOp) and follow(ExprRest) are not disjoint. I get around this by forcing the parse table to only have one entry for + and - which restricts the the syntax of the language but in a predictable way.
ExprRest        -> AddOp Term ExprRest | ε
--------------
Term            -> Factor TermRest
TermRest        -> MultOp Factor TermRest | ε
Factor          -> UnaryOp Factor | ( Expr ) | Atom
--------------
UnaryOp         -> + | -
AddOp           -> + | -
MultOp          -> * | /
Atom            -> NUMBER | STRING | ID | Call

Conditional         -> IF Comparison { ConditionalBody } 
ConditionalRest     -> ELSE { ConditionalBody } | ε
--------------
Comparsion          -> Expr ComparisonTail | Bool
ComparisonTail      -> CompOp Expr ComparisonTail | ε
CompOp              -> GT | LT | GE | LE | EQ | NE
Bool                -> TRUE | FALSE
--------------
ConditionalBody     -> ConditionalEntry ConditionalBody | ε
ConditionalEntry    -> Expr | Assign

Call -> CALL ID ( Args )

Args                   -> ArgList KeyWordArgListTail | KeyWordArgList | ε
ArgList                -> Arg ArgListRest
ArgListRest            -> , Arg ArgListRest | ε 
KeyWordArgListTail     -> | KeyWordArg KeyWordArgListTailRest | ε
KeyWordArgListTailRest -> , KeyWordArg KeyWordArgListTailRest | ε
KeyWordArgList         -> KeyWordArg KeyWordArgListRest
KeyWordArgListRest     -> , KeyWordArg KeyWordArgListRest | ε
Arg                    -> Expr
KeyWordArg             -> Assign
```

I learned how the design of the lexer and the parser influence each other. A knowledge of the type of grammar the parser will use determines the granularity of the tokens the lexer should produce. Because my lexer recognises single-character punctuation, parsing comparison operators like >= and <= would require two tokens of lookahead. To remedy this without having to redesign the parser, I added keyword like operators which are distinguished post lexing – logic which already exists to distinguish keywords from IDs. If and when I refator the compiler, I will consider removing this workaround in favour of more natural comparision operator syntax.

### First and Follow Set Construction

To build the parse table we need first and follow sets for all nonterminals.

We can construct first sets by applying the following rules to all grammar productions:

1) For X -> Y1Y2Y3...Yk, if ε ∈ Yi for i=[1...i-1] , then first(Yi) ⊆ first(X).
2) If ε ∈ Yj for all j =[1...k], then ε ∈ first(X).
3) If X -> ε is a production, then ε is in first(X).

Tip: work on the productions that have shallow derivations first.

First sets:

```
P FUNC, +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, ε
StmtList FUNC, +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, ε
Stmt FUNC, +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF

FuncDef FUNC
FuncBody +, -, (, NUMBER, STRING, ID, CALL, FUNC, RETURN, IF, ASSIGN, ε
FuncEntry +, -, (, NUMBER, STRING, ID, CALL, FUNC, RETURN, ASSIGN, IF

Params ID ASSIGN, ε
ParamList ID
ParamListRest ,, ε
KeyWordParamListTail |, ε
KeyWordParamListTailRest ,, ε
KeyWordParamList ASSIGN
KeyWordParamListRest ,, ε
Param ID
KeyWordParam ASSIGN

Assign ASSIGN

Expr +, -, (, NUMBER, STRING, ID, CALL
ExprRest +, -, ε
Term +, -, (, NUMBER, STRING, ID, CALL
TermRest *, /, ε
Factor +, -, (, NUMBER, STRING, ID, CALL 
UnaryOp +, -
AddOp +, -
MultOp *, /
Atom NUMBER, STRING, ID, CALL

Conditional IF
ConditionalRest ELSE ε
Comparsion +, -, (, NUMBER, STRING, ID, CALL, TRUE, FALSE
ComparisonTail GT, LT, GE, LE, EQ, NE, ε
CompOp GT, LT, GE, LE, EQ, NE
Bool TRUE, FALSE
ConditionalBody +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, ε
ConditionalEntry +, -, (, NUMBER, STRING, ID, CALL, ASSIGN

Call CALL

Args +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, ε
ArgList +, -, (, NUMBER, STRING, ID, CALL
ArgListRest ,, ε
KeyWordArgListTail |, ε
KeyWordArgListTailRest ,, ε
KeyWordArgList ASSIGN
KeyWordArgListRest ,, ε
Arg +, -, (, NUMBER, STRING, ID, CALL
KeyWordArg  ASSIGN
```

To produce the follow sets, first we add $ to follow(S), where S is the start symbol. Then, for all non terminals A, we apply the following rules for all occurences of A. 

1) If there is a production of the form B -> a A c, then all terminals in first(c) are in follow(A) (apart from epsilon).
2) If the production is of the form B -> a A, or B -> a A c where c =>* ε, then all terminals in follow(B) are in follow(A).

Follow sets:

```
P $
StmtList $
Stmt +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $

FuncDef +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $, FUNC, RETURN, }
FuncBody }
FuncEntry +, -, (, NUMBER, STRING, ID, CALL, FUNC, RETURN, IF, ASSIGN, }

Params )
ParamList |, )
ParamListRest |, )
KeyWordParamListTail )
KeyWordParamListTailRest )
KeyWordParamList )
KeyWordParamListRest )
Param ,, |, )
KeyWordParam ,, )

Assign +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $, FUNC, RETURN, }, ,, )

Expr +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $, FUNC, |, RETURN, }, ,, ), GT, LT, GE, LE, EQ, NE, {
ExprRest +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $, FUNC, |, RETURN, }, ,, ), GT, LT, GE, LE, EQ, NE, {
Term +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $, FUNC, |, RETURN, }, ,, ), GT, LT, GE, LE, EQ, NE, {
TermRest +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $, FUNC, |, RETURN, }, ,, ), GT, LT, GE, LE, EQ, NE, {
Factor *, /, +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $, FUNC, |, RETURN, }, ,, ), GT, LT, GE, LE, EQ, NE, {
UnaryOp +, -, (, NUMBER, STRING, ID, CALL
AddOp +, -, (, NUMBER, STRING, ID, CALL
MultOp +, -, (, NUMBER, STRING, ID, CALL
Atom *, /, +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $, FUNC, |, RETURN, }, ,, ), GT, LT, GE, LE, EQ, NE, {

Conditional +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $, FUNC, RETURN, }
ConditionalRest +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $, FUNC, RETURN, }
Comparsion {
ComparisonTail {
CompOp +, -, (, NUMBER, STRING, ID, CALL
Bool {
ConditionalEntry +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, }
ConditionalBody }

Call *, /, +, -, (, NUMBER, STRING, ID, CALL, ASSIGN, IF, $, FUNC, |, RETURN, }, ,, ), GT, LT, GE, LE, EQ, NE, {

Args )
ArgList |, )
ArgListRest |, )
KeyWordArgListTail )
KeyWordArgListTailRest )
KeyWordArgList )
KeyWordArgListRest )
Arg ,, |, )
KeyWordArg ,, )
```

### Parse Table Construction

The first and follow sets are used in a standard algorithm to produce the parse table. I implemented the `parse_table` as a nested dictionary for the same reasons as the state table. The production with head ExprRest has a first/follow conflict because ExprRest =>* ε, and first(AddOp) and follow(ExprRest) are not disjoint. To solve this, I discarded the table entries in follow(ExprRest) which are also in first(AddOp). This means that the compiler can't recognise, as the grammar intends, a new line with an expression that starts with a unary op. This is fine as we can wrap an expression in parentheses as a work around.

### Parsing Logic

The parser is an implementation of a stardard LL(1) parsing procedure. It uses a stack and parse table to expand non terminals or match terminals against the input. The complexity of the parsing algorithm is O(n) with respect to the number of tokens being processed. This is because each token is consumed once, during which, all other operations are constant. The stack is implemented as a list because it provides: O(1) amortised appending, O(1) amortised popping of the last element, and O(1) access to the last element. A deque is equally efficient for these operations but lists have a simpler interface.
The syntax tree is built using the `Node` class which holds references to child nodes. The tree's structure is represented implicitly through object references between nodes removing the need for a separate data structure.

## Modifications to the parser to support AST construction

A raw parse tree is cumbersome due to the presence of nodes with no semantic meaning. Semantic analysis is best performed on an abstract syntax tree (AST): a representation of the program's structure with redundant nodes removed. The set of AST nodes are not necessarily a subset of the parse tree nodes.

### Modified Parser Architecture and Implementation

We could process the parse tree to produce an AST or modify the parser to that its output is an AST. The former results in more modular transparant code at the expense of speed. The latter is faster but more coupled. Given the language is not intended for use in production, the choice between these high level trade offs is not important. I chose to modify the parser to experiment with the coupled architecture. The existing parser utilises an explicit stack so I had to embed semantic actions in the parse table.

There is an alternative architecture which uses neseted functions to parse tokens. In both architectures semantic actions are coupled with grammar structure, but the parse functions make this coupling transparent, leading to more maintainable code. In theory, parse functions are less efficient due to the call stack, however the overhead is neglible for typical inputs. Also languages that implement tail call optimisation will reduce this overhead further. In conclusion, I will maintian the explict stack based parser but I would prefer to use the parse function architecture in a future project.

In absolute terms we have extra work from the semantic stack which handles ast nodes but the asymptotic time and space complexity remain the same. This is because the number of times we process a semantic action grows linearly with the number tokens that expand to a production containing said semantic action. All semantic actions are processed in constant time, and therfore, the time complexity of AST construction is O(n), where n is the number of tokens.

Semantic actions are triggered during parsing by embedding markers into the parse table. The markers are implemented in several Enums, one for clearly defined type of action. For example, Any marker that corresponds to an action which accepts a list of semantic values and returns an AST node is a member of the `NonTerminalMarkers` Enum. Markers and corresponding actions are bound as key value pairs in the dictionary `parser_markers_to_actions`. The dictionary is better than a switch statment for large grammars, assuming that a larger grammar implies more parser actions. Parser actions use integer indexing to access objects from their input. This is error prone but manageable for this size project. We could implement specific accumulator lists for each action with named access.

## Error Handling

All errors inherit from `CompilationError`, which exposes an `.errors` property returning a `list[CompilationError]`. This gives callers a single, uniform way to iterate errors regardless of which phase raised them.

Lexer and parser errors (`LexError`, `ParseError`) inherit from `SourceError`, which carries a `SourcePos(line, col)` pinpointing where things went wrong. These phases fail immediately, since there's no sensible way to continue after an unexpected character or grammar violation.

The semantic analyser works differently. It collects individual `SemanticError` instances into a list as it walks the tree, then raises a `CompilationError(errors=...)` at the end. This way you see all type mismatches and undefined variables in one pass instead of fixing them one at a time.
