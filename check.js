const { Client } = require('pg');
const client = new Client({ connectionString: 'postgres://plataforma_educativa_cea_user:iL7jWwQ0oX6jWvX5gX3f7T4rB2hV8rQ6@dpg-c09q43r4m5t7j0i3k83g-a.oregon-postgres.render.com/plataforma_educativa_cea_db', ssl: { rejectUnauthorized: false } });
client.connect()
  .then(() => client.query(`SELECT i.usuario_id, u.nombre, u.apellido, i.turno FROM inscripciones i JOIN usuarios u ON u.id = i.usuario_id WHERE u.apellido LIKE 'MENACHO%'`))
  .then(res => { console.log(res.rows); client.end(); })
  .catch(console.error);
