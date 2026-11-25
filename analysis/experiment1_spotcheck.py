"""Spot-check timestamp precision and the live command-stage dispatch before fitting."""
import ast
import sys
from pathlib import Path
import duckdb

def check(cache):
    path = sorted(Path(cache).glob("*.json.gz"))[0]
    db = duckdb.connect()
    db.execute("""create table e as select sensor,session,ts::timestamp t,eventid from
        read_json(?,columns={sensor:'varchar',session:'varchar',ts:'varchar',eventid:'varchar'},
        format='newline_delimited') limit 100000""", [str(path)])
    for name, predicate, index in [('S2',"eventid in ('cowrie.login.success','cowrie.login.failed')",1),
                                   ('S4',"eventid='cowrie.command.input'",1),('S5',"eventid='cowrie.command.input'",3)]:
        print(name, db.execute(f"""with a as (select sensor, session,(list(t order by t))[{index}] anchor
          from e where {predicate} group by all), counts as (select a.sensor,a.session,
          count(*) n,count(*) filter(where t=anchor) exact from a join e using(sensor,session)
          where date_trunc('second',t)=date_trunc('second',anchor) group by all)
          select count(*),count(*) filter(where n>1),count(*) filter(where exact>1) from counts""").fetchone())
    expression = next(n.value for n in ast.walk(ast.parse(Path('sensor/adaptive_server.py').read_text()))
                      if isinstance(n,ast.Assign) and isinstance(n.value,ast.IfExp)
                      and ast.unparse(n.value.body)=="'S4'")
    print("first live S5",next(i for i in range(1,5) if eval(compile(ast.Expression(expression),
          '<dispatch>','eval'),{'self':type('Adapter',(),{'commands_history':[None]*i})})=='S5'))
if __name__=='__main__':
    check(sys.argv[1])
